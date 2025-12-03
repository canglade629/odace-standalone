"""Bronze pipeline for transport data (gares and lignes) from Open Data API."""
import pandas as pd
import re
from app.pipelines.base_api import BaseAPIBronzePipeline
from app.core.pipeline_registry import register_pipeline
import logging

logger = logging.getLogger(__name__)


@register_pipeline(layer="bronze", name="gares")
class BronzeGaresPipeline(BaseAPIBronzePipeline):
    """Ingests gares (train stations) data from Open Data API into bronze layer."""
    
    # SNCF Gares resource ID from data.gouv.fr
    RESOURCE_ID = "d22ba593-90a4-4725-977c-095d1f654d28"
    
    def __init__(self):
        """Initialize with Open Data API configuration."""
        super().__init__()
        # Override rate limiter for Open Data API (100 req/sec)
        from app.pipelines.base_api import RateLimiter
        self.rate_limiter = RateLimiter(
            max_requests=self.settings.open_data_api_rate_limit,
            time_window=1  # 1 second window
        )
    
    def get_name(self) -> str:
        return "bronze_gares"
    
    def get_source_path(self) -> str:
        return f"api://open_data/{self.RESOURCE_ID}"
    
    def get_target_table(self) -> str:
        return "gares"
    
    def get_api_endpoint(self) -> str:
        """Get the API endpoint for SNCF gares resource."""
        return f"/resources/{self.RESOURCE_ID}/data/"
    
    def get_api_params(self) -> dict:
        """Get query parameters for API request."""
        return {'page_size': 100}
    
    async def fetch_all_data(self):
        """Fetch all data from Open Data API."""
        import httpx
        import asyncio
        
        base_url = self.settings.open_data_api_base_url
        endpoint = self.get_api_endpoint()
        url = f"{base_url}{endpoint}"
        params = self.get_api_params()
        
        all_records = []
        page = 1
        
        async with httpx.AsyncClient() as client:
            self.client = client
            
            while True:
                page_params = {**params, "page": page}
                logger.info(f"Fetching page {page}...")
                response_data = await self.fetch_page(url, page_params)
                
                records = response_data.get("data", [])
                if not records:
                    break
                
                all_records.extend(records)
                
                meta = response_data.get("meta", {})
                total = meta.get("total", "unknown")
                logger.info(f"Fetched {len(all_records)} / {total} records")
                
                if not response_data.get("links", {}).get("next"):
                    break
                
                page += 1
        
        logger.info(f"Fetched {len(all_records)} total records")
        return all_records
    
    def transform(self, df: pd.DataFrame, file_path: str) -> pd.DataFrame:
        """Normalize column names and convert types to match Databricks schema."""
        # Normalize column names: lowercase, replace non-alphanumeric with underscores
        normalized_cols = [re.sub(r'[^a-zA-Z0-9]', '_', c).lower() for c in df.columns]
        df.columns = normalized_cols
        
        # Convert numeric columns to string to match Databricks schema
        if 'code_uic' in df.columns:
            df['code_uic'] = df['code_uic'].astype(str)
        if 'code_ligne' in df.columns:
            df['code_ligne'] = df['code_ligne'].astype(str)
        if 'idreseau' in df.columns:
            df['idreseau'] = df['idreseau'].astype(str)
        
        # Add ingestion timestamp
        df = super().transform(df, file_path)
        
        logger.info(f"Normalized columns: {list(df.columns)}")
        return df

@register_pipeline(layer="bronze", name="lignes")
class BronzeLignesPipeline(BaseAPIBronzePipeline):
    """Ingests lignes (train lines) data from Open Data API into bronze layer."""
    
    # SNCF Lignes resource ID from data.gouv.fr
    RESOURCE_ID = "2f204d3f-4274-42fb-934f-4a73954e0c4e"
    
    def __init__(self):
        """Initialize with Open Data API configuration."""
        super().__init__()
        # Override rate limiter for Open Data API (100 req/sec)
        from app.pipelines.base_api import RateLimiter
        self.rate_limiter = RateLimiter(
            max_requests=self.settings.open_data_api_rate_limit,
            time_window=1  # 1 second window
        )
    
    def get_name(self) -> str:
        return "bronze_lignes"
    
    def get_source_path(self) -> str:
        return f"api://open_data/{self.RESOURCE_ID}"
    
    def get_target_table(self) -> str:
        return "lignes"
    
    def get_api_endpoint(self) -> str:
        """Get the API endpoint for SNCF lignes resource."""
        return f"/resources/{self.RESOURCE_ID}/data/"
    
    def get_api_params(self) -> dict:
        """Get query parameters for API request."""
        return {'page_size': 100}
    
    async def fetch_all_data(self):
        """Fetch all data from Open Data API."""
        import httpx
        import asyncio
        
        base_url = self.settings.open_data_api_base_url
        endpoint = self.get_api_endpoint()
        url = f"{base_url}{endpoint}"
        params = self.get_api_params()
        
        all_records = []
        page = 1
        
        async with httpx.AsyncClient() as client:
            self.client = client
            
            while True:
                page_params = {**params, "page": page}
                logger.info(f"Fetching page {page}...")
                response_data = await self.fetch_page(url, page_params)
                
                records = response_data.get("data", [])
                if not records:
                    break
                
                all_records.extend(records)
                
                meta = response_data.get("meta", {})
                total = meta.get("total", "unknown")
                logger.info(f"Fetched {len(all_records)} / {total} records")
                
                if not response_data.get("links", {}).get("next"):
                    break
                
                page += 1
        
        logger.info(f"Fetched {len(all_records)} total records")
        return all_records
    
    def transform(self, df: pd.DataFrame, file_path: str) -> pd.DataFrame:
        """Normalize column names and convert types to match Databricks schema."""
        # Normalize column names: lowercase, replace non-alphanumeric with underscores
        normalized_cols = [re.sub(r'[^a-zA-Z0-9]', '_', c).lower() for c in df.columns]
        df.columns = normalized_cols
        
        # Convert code_ligne to string to match Databricks schema
        if 'code_ligne' in df.columns:
            df['code_ligne'] = df['code_ligne'].astype(str)
        
        # Add ingestion timestamp
        df = super().transform(df, file_path)
        
        logger.info(f"Normalized columns: {list(df.columns)}")
        return df

