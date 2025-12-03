"""Bronze pipeline for Open Data API ingestion (data.gouv.fr)."""
import pandas as pd
import httpx
import asyncio
from typing import Dict, Any, List, Optional
import logging

from app.pipelines.base_api import BaseAPIBronzePipeline, RateLimiter
from app.core.config import get_settings
from app.core.pipeline_registry import register_pipeline

logger = logging.getLogger(__name__)


# DO NOT register this as a pipeline - it's a base class for specific resource pipelines
# Use BronzeGaresPipeline, BronzeLignesPipeline etc instead
class BronzeOpenDataPipeline(BaseAPIBronzePipeline):
    """
    Generic bronze pipeline for ingesting data from data.gouv.fr tabular API.
    
    Supports multiple resources configured in open_data_sources.yaml.
    Each resource is fetched as a separate table in the bronze layer.
    """
    
    def __init__(self, resource_id: Optional[str] = None):
        """
        Initialize Open Data pipeline.
        
        Args:
            resource_id: Optional specific resource ID to fetch. If None, fetches all configured resources.
        """
        super().__init__()
        self.resource_id = resource_id
        self.resource_config = None
        
        # Override rate limiter for Open Data API (100 req/sec instead of 12 req/min)
        self.rate_limiter = RateLimiter(
            max_requests=self.settings.open_data_api_rate_limit,
            time_window=1  # 1 second window for 100 req/sec
        )
        
        # Load resource configuration
        if resource_id:
            resources = self.settings.load_open_data_sources()
            for res in resources:
                if res.get('resource_id') == resource_id:
                    self.resource_config = res
                    break
            
            if not self.resource_config:
                logger.warning(f"Resource {resource_id} not found in configuration")
                # Create a minimal config
                self.resource_config = {
                    'resource_id': resource_id,
                    'name': f'resource_{resource_id[:8]}',
                    'description': 'Unknown resource'
                }
    
    def get_name(self) -> str:
        """Get pipeline name."""
        if self.resource_config:
            return f"bronze_open_data_{self.resource_config['name']}"
        return "bronze_open_data"
    
    def get_source_path(self) -> str:
        """Override to return API marker."""
        if self.resource_config:
            return f"api://open_data/{self.resource_config['resource_id']}"
        return "api://open_data"
    
    def get_target_table(self) -> str:
        """Get target Delta table name."""
        if self.resource_config:
            return f"open_data_{self.resource_config['name']}"
        return "open_data"
    
    def get_api_endpoint(self) -> str:
        """
        Get the API endpoint for the specific resource.
        
        Returns:
            API endpoint path (e.g., "/resources/{resource_id}/data/")
        """
        if not self.resource_config:
            raise ValueError("No resource configuration available. Provide resource_id.")
        
        return f"/resources/{self.resource_config['resource_id']}/data/"
    
    def get_api_params(self) -> Dict[str, Any]:
        """
        Get query parameters for API request.
        
        For data.gouv.fr, we'll use larger page sizes to minimize requests.
        
        Returns:
            Dictionary of query parameters
        """
        return {
            'page_size': 100  # Maximum reasonable page size (default is 20)
        }
    
    async def fetch_all_data(self) -> List[Dict[str, Any]]:
        """
        Fetch all data from the Open Data API, handling pagination.
        
        The data.gouv.fr API uses a different pagination structure:
        {
          "data": [...],
          "links": {"next": "...", "prev": "..."},
          "meta": {"page": 1, "page_size": 20, "total": N}
        }
        
        Returns:
            List of records
        """
        base_url = self.settings.open_data_api_base_url
        endpoint = self.get_api_endpoint()
        url = f"{base_url}{endpoint}"
        params = self.get_api_params()
        
        all_records = []
        page = 1
        
        async with httpx.AsyncClient() as client:
            self.client = client
            
            while True:
                # Add pagination parameter
                page_params = {**params, "page": page}
                
                logger.info(f"Fetching page {page}...")
                response_data = await self.fetch_page(url, page_params)
                
                # Extract data from response
                if not isinstance(response_data, dict):
                    logger.warning(f"Unexpected response type: {type(response_data)}")
                    break
                
                records = response_data.get("data", [])
                if not records:
                    logger.info("No more records to fetch")
                    break
                
                all_records.extend(records)
                
                # Log progress
                meta = response_data.get("meta", {})
                total = meta.get("total", "unknown")
                logger.info(f"Fetched {len(all_records)} / {total} records")
                
                # Check if there are more pages
                links = response_data.get("links", {})
                if not links.get("next"):
                    logger.info("Reached last page")
                    break
                
                page += 1
        
        logger.info(f"Fetched {len(all_records)} total records")
        return all_records
    
    def normalize_json_to_dataframe(self, records: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Convert list of JSON records to pandas DataFrame.
        
        The Open Data API includes a special __id field that we'll keep.
        
        Args:
            records: List of JSON records
            
        Returns:
            pandas DataFrame
        """
        if not records:
            logger.warning("No records to normalize")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(records)
        
        # Remove quotes from column names if present (some Open Data sources add them)
        df.columns = df.columns.str.strip('"')
        
        logger.info(f"Normalized {len(df)} records with {len(df.columns)} columns")
        logger.debug(f"Columns: {list(df.columns)}")
        
        return df
    
    def get_write_mode(self) -> str:
        """
        Open Data API pipelines should overwrite data (full refresh).
        
        Returns:
            Write mode: 'overwrite'
        """
        return "overwrite"
    
    @classmethod
    def run_all_resources(cls, force: bool = False) -> Dict[str, Any]:
        """
        Run ingestion for all configured Open Data resources.
        
        Args:
            force: Force reprocessing
            
        Returns:
            Dictionary with results for each resource
        """
        settings = get_settings()
        resources = settings.load_open_data_sources()
        
        if not resources:
            logger.warning("No Open Data resources configured")
            return {
                "status": "warning",
                "message": "No resources configured in open_data_sources.yaml"
            }
        
        results = {}
        
        for resource in resources:
            resource_id = resource.get('resource_id')
            resource_name = resource.get('name', resource_id)
            
            logger.info(f"Processing resource: {resource_name} ({resource_id})")
            
            try:
                pipeline = cls(resource_id=resource_id)
                result = pipeline.run(force=force)
                results[resource_name] = result
            except Exception as e:
                logger.error(f"Error processing resource {resource_name}: {e}", exc_info=True)
                results[resource_name] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        # Aggregate results
        total_success = sum(1 for r in results.values() if r.get("status") == "success")
        total_failed = sum(1 for r in results.values() if r.get("status") == "failed")
        
        return {
            "status": "success" if total_failed == 0 else "partial",
            "resources_processed": len(results),
            "resources_success": total_success,
            "resources_failed": total_failed,
            "results": results
        }

