"""Bronze pipeline for transport data (gares and lignes)."""
import pandas as pd
import re
from app.pipelines.base import BaseBronzePipeline
from app.core.pipeline_registry import register_pipeline
import logging

logger = logging.getLogger(__name__)


@register_pipeline(layer="bronze", name="gares")
class BronzeGaresPipeline(BaseBronzePipeline):
    """Ingests gares (train stations) CSV data into bronze layer."""
    
    def get_name(self) -> str:
        return "bronze_gares"
    
    def get_source_path(self) -> str:
        return self.settings.get_raw_path("transport/gares")
    
    def get_target_table(self) -> str:
        return "gares"
    
    def read_source_file(self, file_path: str) -> pd.DataFrame:
        """Read CSV file from GCS."""
        logger.info(f"Reading CSV file: {file_path}")
        
        # Download file to memory
        file_content = self.gcs.download_file(file_path)
        
        # Read CSV with semicolon delimiter
        df = pd.read_csv(
            pd.io.common.BytesIO(file_content),
            delimiter=';',
            header=0
        )
        
        logger.info(f"Read {len(df)} rows with {len(df.columns)} columns")
        return df
    
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
class BronzeLignesPipeline(BaseBronzePipeline):
    """Ingests lignes (train lines) CSV data into bronze layer."""
    
    def get_name(self) -> str:
        return "bronze_lignes"
    
    def get_source_path(self) -> str:
        return self.settings.get_raw_path("transport/lignes")
    
    def get_target_table(self) -> str:
        return "lignes"
    
    def read_source_file(self, file_path: str) -> pd.DataFrame:
        """Read CSV file from GCS."""
        logger.info(f"Reading CSV file: {file_path}")
        
        # Download file to memory
        file_content = self.gcs.download_file(file_path)
        
        # Read CSV with semicolon delimiter
        df = pd.read_csv(
            pd.io.common.BytesIO(file_content),
            delimiter=';',
            header=0
        )
        
        logger.info(f"Read {len(df)} rows with {len(df.columns)} columns")
        return df
    
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

