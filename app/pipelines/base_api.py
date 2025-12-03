"""Base pipeline class for API-based data ingestion."""
import pandas as pd
import httpx
import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from abc import abstractmethod
import logging

from app.pipelines.base import BaseBronzePipeline
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter for API calls.
    
    Ensures we don't exceed the specified rate limit (e.g., 12 requests per minute).
    """
    
    def __init__(self, max_requests: int, time_window: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed in time_window
            time_window: Time window in seconds (default: 60 seconds)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: List[float] = []
    
    async def acquire(self):
        """
        Acquire permission to make a request.
        
        Will sleep if necessary to stay within rate limits.
        """
        now = time.time()
        
        # Remove requests outside the time window
        self.requests = [req_time for req_time in self.requests if now - req_time < self.time_window]
        
        if len(self.requests) >= self.max_requests:
            # Calculate how long to wait
            oldest_request = self.requests[0]
            wait_time = self.time_window - (now - oldest_request) + 0.1  # Add 100ms buffer
            
            if wait_time > 0:
                logger.info(f"Rate limit reached. Waiting {wait_time:.2f} seconds...")
                await asyncio.sleep(wait_time)
                
                # Clean up again after waiting
                now = time.time()
                self.requests = [req_time for req_time in self.requests if now - req_time < self.time_window]
        
        # Record this request
        self.requests.append(time.time())


class BaseAPIBronzePipeline(BaseBronzePipeline):
    """
    Base class for bronze pipelines that fetch data from REST APIs.
    
    Provides:
    - HTTP client with retry logic
    - Rate limiting
    - Pagination handling
    - JSON to DataFrame conversion
    """
    
    def __init__(self):
        """Initialize API pipeline."""
        super().__init__()
        self.settings = get_settings()
        self.rate_limiter = RateLimiter(
            max_requests=self.settings.siae_api_rate_limit,
            time_window=60
        )
        self.client = None
    
    def get_source_path(self) -> str:
        """
        Override to return a dummy path for API sources.
        
        API pipelines don't read from GCS files, so we return a marker.
        """
        return "api://siae"
    
    @abstractmethod
    def get_api_endpoint(self) -> str:
        """
        Get the API endpoint path (relative to base URL).
        
        Returns:
            API endpoint path (e.g., "/siaes/")
        """
        pass
    
    def get_api_params(self) -> Dict[str, Any]:
        """
        Get query parameters for API request.
        
        Override this method to customize API parameters.
        
        Returns:
            Dictionary of query parameters
        """
        return {}
    
    def get_max_retries(self) -> int:
        """
        Get maximum number of retries for failed requests.
        
        Returns:
            Number of retries (default: 3)
        """
        return 3
    
    def get_retry_delay(self) -> float:
        """
        Get delay between retries in seconds.
        
        Returns:
            Retry delay in seconds (default: 2.0)
        """
        return 2.0
    
    async def fetch_page(self, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fetch a single page from the API with retry logic.
        
        Args:
            url: Full URL to fetch
            params: Query parameters
            
        Returns:
            JSON response as dictionary
            
        Raises:
            Exception: If all retries fail
        """
        max_retries = self.get_max_retries()
        retry_delay = self.get_retry_delay()
        
        for attempt in range(max_retries):
            try:
                # Wait for rate limiter
                await self.rate_limiter.acquire()
                
                # Make request
                logger.debug(f"Fetching {url} with params {params}")
                response = await self.client.get(url, params=params, timeout=30.0)
                response.raise_for_status()
                
                return response.json()
                
            except httpx.HTTPStatusError as e:
                logger.warning(f"HTTP error on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    raise
                    
            except httpx.RequestError as e:
                logger.warning(f"Request error on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                else:
                    raise
    
    async def fetch_all_data(self) -> List[Dict[str, Any]]:
        """
        Fetch all data from the API, handling pagination.
        
        Override this method if the API has non-standard pagination.
        
        Returns:
            List of records
        """
        base_url = self.settings.siae_api_base_url
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
                data = await self.fetch_page(url, page_params)
                
                # Extract results (adjust based on API response structure)
                # Common patterns: {"results": [...], "next": "...", "count": N}
                if isinstance(data, dict):
                    if "results" in data:
                        records = data["results"]
                        all_records.extend(records)
                        
                        # Check if there are more pages
                        if not data.get("next") or not records:
                            break
                        
                        page += 1
                    else:
                        # If response is a dict but not paginated, use the whole thing
                        all_records.append(data)
                        break
                elif isinstance(data, list):
                    # If response is a list, use it directly
                    all_records.extend(data)
                    break
                else:
                    logger.warning(f"Unexpected API response type: {type(data)}")
                    break
        
        logger.info(f"Fetched {len(all_records)} total records")
        return all_records
    
    def normalize_json_to_dataframe(self, records: List[Dict[str, Any]]) -> pd.DataFrame:
        """
        Convert list of JSON records to pandas DataFrame.
        
        Handles nested structures by flattening them.
        Override this method for custom normalization logic.
        
        Args:
            records: List of JSON records
            
        Returns:
            pandas DataFrame
        """
        if not records:
            # Return empty DataFrame with no columns
            logger.warning("No records to normalize")
            return pd.DataFrame()
        
        # Use pandas json_normalize for basic flattening
        df = pd.json_normalize(records, sep='_')
        
        logger.info(f"Normalized {len(df)} records with {len(df.columns)} columns")
        return df
    
    def save_raw_data(self, records: List[Dict[str, Any]], table_name: str) -> str:
        """
        Save raw JSON data to GCS raw layer with timestamp.
        
        Args:
            records: List of JSON records
            table_name: Name of the target table
            
        Returns:
            GCS path where raw data was saved
        """
        import json
        from datetime import datetime
        
        # Generate timestamped filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        filename = f"{table_name}_{timestamp}.json"
        
        # Construct raw path
        raw_path = f"{self.settings.raw_path}/api/{table_name}/{filename}"
        
        # Convert records to JSON
        json_content = json.dumps(records, indent=2, ensure_ascii=False)
        
        # Upload to GCS
        logger.info(f"Saving raw data to {raw_path}")
        self.gcs.upload_from_string(json_content, raw_path)
        
        logger.info(f"Saved {len(records)} records to {raw_path}")
        return raw_path
    
    def read_source_file(self, file_path: str) -> pd.DataFrame:
        """
        Read data for API pipeline with smart caching:
        1. Check if raw files exist in GCS -> use them
        2. If no raw files, fetch from API and save to raw
        
        Args:
            file_path: Path marker (for API pipelines, indicates whether to fetch)
            
        Returns:
            pandas DataFrame with data
        """
        table_name = self.get_target_table()
        raw_base_path = f"{self.settings.raw_path}/api/{table_name}"
        
        # Check if raw files already exist
        try:
            logger.info(f"Checking for existing raw files in {raw_base_path}")
            raw_files = self.gcs.list_files(raw_base_path, pattern="*.json")
            
            if raw_files:
                # Use the most recent raw file
                latest_raw_file = sorted(raw_files)[-1]
                logger.info(f"Found existing raw file: {latest_raw_file}. Using cached data (skip API call).")
                
                # Read from raw file
                import json
                raw_content = self.gcs.download_file(latest_raw_file)
                records = json.loads(raw_content)
                
                # Convert to DataFrame
                df = self.normalize_json_to_dataframe(records)
                return df
                
        except Exception as e:
            logger.info(f"No raw files found or error reading them: {e}")
        
        # No raw files exist - fetch from API
        logger.info(f"No cached data found. Fetching fresh data from API: {self.get_api_endpoint()}")
        
        # Fetch data asynchronously
        records = asyncio.run(self.fetch_all_data())
        
        # Save raw data to GCS raw layer
        self.save_raw_data(records, table_name)
        
        # Convert to DataFrame
        df = self.normalize_json_to_dataframe(records)
        
        return df
    
    def get_new_files(self, force: bool = False) -> List[str]:
        """
        Determine if API pipeline should process data.
        
        Logic (smart caching):
        1. If force=True: Always process (will trigger API fetch via read_source_file)
        2. Check bronze table:
           - If exists with data: Skip (bronze cache hit)
           - If doesn't exist or empty: Process (will check raw, then API in read_source_file)
        
        Args:
            force: If True, force reprocessing (triggers fresh API fetch)
            
        Returns:
            List with single marker string, or empty list if no processing needed
        """
        # For API sources, we use a timestamp-based marker
        marker = f"api_fetch_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        if force:
            logger.info("Force mode: will fetch fresh data from API")
            return [marker]
        
        # Check if bronze table already exists
        table_name = self.get_target_table()
        target_path = self.settings.get_bronze_path(table_name)
        
        try:
            from app.utils.delta_ops import DeltaOperations
            table_info = DeltaOperations.get_table_schema(target_path)
            row_count = table_info.get("row_count", 0)
            
            if row_count > 0:
                logger.info(f"Bronze table {table_name} already exists with {row_count} rows. Skipping processing.")
                return []  # Skip - bronze cache hit
            else:
                logger.info(f"Bronze table {table_name} exists but is empty. Processing (will check raw cache).")
                return [marker]
                
        except Exception as e:
            logger.info(f"Bronze table {table_name} not found ({e}). Processing (will check raw cache, then API).")
            return [marker]
    
    def get_write_mode(self) -> str:
        """
        API pipelines should overwrite data (full refresh).
        
        Returns:
            Write mode: 'overwrite'
        """
        return "overwrite"

