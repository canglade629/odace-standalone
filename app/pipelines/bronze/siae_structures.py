"""Bronze pipeline for SIAE structures data."""
import pandas as pd
import asyncio
import httpx
from typing import List, Dict, Any
from app.pipelines.base_api import BaseAPIBronzePipeline
from app.core.pipeline_registry import register_pipeline
import logging

logger = logging.getLogger(__name__)


@register_pipeline(layer="bronze", name="siae_structures")
class BronzeSIAEStructuresPipeline(BaseAPIBronzePipeline):
    """
    Ingests SIAE structures data from emplois.inclusion.beta.gouv.fr API.
    
    Fetches data about social inclusion employment structures including:
    - SIRET number
    - Structure type
    - Legal and trade names
    - Address and coordinates
    - Recruitment status
    - Job positions offered
    """
    
    def get_name(self) -> str:
        return "bronze_siae_structures"
    
    def get_target_table(self) -> str:
        return "siae_structures"
    
    def get_api_endpoint(self) -> str:
        return "/siaes/"
    
    def get_french_departments(self) -> list:
        """
        Get list of French department codes.
        
        Returns all metropolitan and overseas departments.
        """
        # Metropolitan departments: 01-95 (excluding 20 which is split into 2A/2B)
        metropolitan = [f"{i:02d}" for i in range(1, 20)] + ["2A", "2B"] + [f"{i:02d}" for i in range(21, 96)]
        # Overseas departments
        overseas = ["971", "972", "973", "974", "976"]
        return metropolitan + overseas
    
    def get_api_params(self) -> dict:
        """
        Get API parameters.
        
        The /siaes/ endpoint requires either:
        - code_insee + distance_max_km
        - departement
        - postes_dans_le_departement
        
        We'll fetch by department to get all structures.
        """
        # This will be overridden during fetch to iterate through departments
        return {}
    
    async def fetch_all_data(self) -> List[Dict[str, Any]]:
        """
        Fetch all SIAE structures by iterating through all French departments.
        
        The API requires a department filter, so we query each department separately.
        """
        base_url = self.settings.siae_api_base_url
        endpoint = self.get_api_endpoint()
        url = f"{base_url}{endpoint}"
        
        all_records = []
        departments = self.get_french_departments()
        
        async with httpx.AsyncClient() as client:
            self.client = client
            
            for dept in departments:
                logger.info(f"Fetching SIAE structures for department {dept}...")
                
                try:
                    # Fetch for this department
                    await self.rate_limiter.acquire()
                    
                    params = {"departement": dept}
                    response = await client.get(url, params=params, timeout=30.0)
                    response.raise_for_status()
                    
                    data = response.json()
                    
                    # Handle different response structures
                    if isinstance(data, dict) and "results" in data:
                        records = data["results"]
                    elif isinstance(data, list):
                        records = data
                    else:
                        logger.warning(f"Unexpected response type for dept {dept}: {type(data)}")
                        continue
                    
                    logger.info(f"  Found {len(records)} structures in department {dept}")
                    all_records.extend(records)
                    
                except httpx.HTTPStatusError as e:
                    logger.warning(f"HTTP error for department {dept}: {e}")
                    # Continue with next department
                except Exception as e:
                    logger.error(f"Error fetching department {dept}: {e}")
                    # Continue with next department
        
        logger.info(f"Fetched {len(all_records)} total SIAE structures across all departments")
        return all_records
    
    def normalize_json_to_dataframe(self, records: list) -> pd.DataFrame:
        """
        Normalize SIAE structures JSON to flat DataFrame.
        
        Handles nested structures like address, jobs, etc.
        """
        if not records:
            logger.warning("No SIAE structures records received")
            return pd.DataFrame()
        
        # Flatten nested JSON
        df = pd.json_normalize(
            records,
            sep='_',
            max_level=2  # Limit flattening depth to avoid overly nested columns
        )
        
        logger.info(f"Normalized {len(df)} SIAE structures records with {len(df.columns)} columns")
        logger.debug(f"Columns: {list(df.columns)}")
        
        return df

