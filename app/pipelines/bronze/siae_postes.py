"""Bronze pipeline for SIAE postes (job positions) data."""
import pandas as pd
import asyncio
import httpx
from typing import List, Dict, Any
from app.pipelines.base_api import BaseAPIBronzePipeline
from app.core.pipeline_registry import register_pipeline
import logging

logger = logging.getLogger(__name__)


@register_pipeline(layer="bronze", name="siae_postes")
class BronzeSIAEPostesPipeline(BaseAPIBronzePipeline):
    """
    Ingests SIAE job positions data by exploding the postes field from structures.
    
    Fetches structures and then explodes the nested postes array to create
    a separate table with one row per job position.
    """
    
    def get_name(self) -> str:
        return "bronze_siae_postes"
    
    def get_target_table(self) -> str:
        return "siae_postes"
    
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
        """Get API parameters."""
        return {}
    
    async def fetch_all_data(self) -> List[Dict[str, Any]]:
        """
        Fetch all SIAE structures and extract postes (job positions).
        
        Returns a flattened list of postes with structure references.
        """
        base_url = self.settings.siae_api_base_url
        endpoint = self.get_api_endpoint()
        url = f"{base_url}{endpoint}"
        
        all_postes = []
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
                        structures = data["results"]
                    elif isinstance(data, list):
                        structures = data
                    else:
                        logger.warning(f"Unexpected response type for dept {dept}: {type(data)}")
                        continue
                    
                    # Extract postes from each structure
                    for structure in structures:
                        structure_id = structure.get('id')
                        siret = structure.get('siret')
                        postes = structure.get('postes', [])
                        
                        # Add structure reference to each poste
                        for poste in postes:
                            poste_with_ref = {
                                'structure_id': structure_id,
                                'structure_siret': siret,
                                **poste
                            }
                            all_postes.append(poste_with_ref)
                    
                    logger.info(f"  Extracted postes from {len(structures)} structures in department {dept}")
                    
                except httpx.HTTPStatusError as e:
                    logger.warning(f"HTTP error for department {dept}: {e}")
                except Exception as e:
                    logger.error(f"Error fetching department {dept}: {e}")
        
        logger.info(f"Extracted {len(all_postes)} total job positions across all departments")
        return all_postes
    
    def normalize_json_to_dataframe(self, records: list) -> pd.DataFrame:
        """
        Normalize job positions JSON to flat DataFrame.
        """
        if not records:
            logger.warning("No SIAE postes records received")
            return pd.DataFrame()
        
        # Flatten nested JSON
        df = pd.json_normalize(
            records,
            sep='_',
            max_level=2
        )
        
        logger.info(f"Normalized {len(df)} SIAE postes records with {len(df.columns)} columns")
        logger.debug(f"Columns: {list(df.columns)}")
        
        return df

