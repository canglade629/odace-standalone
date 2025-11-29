"""Bronze pipeline for logement (housing) data."""
import pandas as pd
import re
from datetime import datetime
from app.pipelines.base import BaseBronzePipeline
from app.core.pipeline_registry import register_pipeline
import logging

logger = logging.getLogger(__name__)


@register_pipeline(layer="bronze", name="logement")
class BronzeLogementPipeline(BaseBronzePipeline):
    """Ingests logement CSV data with timestamp extraction into bronze layer."""
    
    def get_name(self) -> str:
        return "bronze_logement"
    
    def get_source_path(self) -> str:
        return self.settings.get_raw_path("logement")
    
    def get_target_table(self) -> str:
        return "logement"
    
    def read_source_file(self, file_path: str) -> pd.DataFrame:
        """Read CSV file from GCS with encoding fallback."""
        logger.info(f"Reading CSV file: {file_path}")
        
        # Download file to memory
        file_content = self.gcs.download_file(file_path)
        
        # Try UTF-8 first, then fallback to Latin-1 (ISO-8859-1)
        try:
            df = pd.read_csv(
                pd.io.common.BytesIO(file_content),
                delimiter=';',
                header=0,
                encoding='utf-8'
            )
            logger.info(f"Read CSV with UTF-8 encoding")
        except UnicodeDecodeError:
            logger.warning(f"UTF-8 decoding failed, trying Latin-1")
            df = pd.read_csv(
                pd.io.common.BytesIO(file_content),
                delimiter=';',
                header=0,
                encoding='latin1'
            )
            logger.info(f"Read CSV with Latin-1 encoding")
        
        logger.info(f"Read {len(df)} rows with {len(df.columns)} columns")
        return df
    
    def transform(self, df: pd.DataFrame, file_path: str) -> pd.DataFrame:
        """
        Transform with timestamp extraction from filename.
        
        Extracts timestamp from filename pattern: *_YYYYMMDD_HHMMSS.csv
        """
        # Try to extract timestamp from filename
        filename = file_path.split('/')[-1]
        match = re.search(r'_(\d{8}_\d{6})', filename)
        
        if match:
            timestamp_str = match.group(1)
            try:
                ingestion_timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                logger.info(f"Extracted timestamp from filename: {ingestion_timestamp}")
            except ValueError:
                logger.warning(f"Could not parse timestamp: {timestamp_str}")
                ingestion_timestamp = datetime.utcnow()
        else:
            logger.warning(f"No timestamp found in filename: {filename}")
            ingestion_timestamp = datetime.utcnow()
        
        df['ingestion_timestamp'] = ingestion_timestamp
        
        return df

