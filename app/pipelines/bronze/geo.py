"""Bronze pipeline for geographic data."""
import pandas as pd
from app.pipelines.base import BaseBronzePipeline
from app.core.pipeline_registry import register_pipeline
import logging

logger = logging.getLogger(__name__)


@register_pipeline(layer="bronze", name="geo")
class BronzeGeoPipeline(BaseBronzePipeline):
    """Ingests geographic/communes CSV data into bronze layer."""
    
    def get_name(self) -> str:
        return "bronze_geo"
    
    def get_source_path(self) -> str:
        return self.settings.get_raw_path("geo")
    
    def get_target_table(self) -> str:
        return "geo"
    
    def read_source_file(self, file_path: str) -> pd.DataFrame:
        """Read CSV file from GCS with auto-delimiter detection."""
        logger.info(f"Reading CSV file: {file_path}")
        
        # Download file to memory
        file_content = self.gcs.download_file(file_path)
        
        # Try to auto-detect delimiter (common ones: comma, semicolon, tab)
        # First try pandas' engine='python' with sep=None for auto-detection
        try:
            df = pd.read_csv(
                pd.io.common.BytesIO(file_content),
                header=0,
                sep=None,  # Auto-detect delimiter
                engine='python',
                encoding='utf-8-sig',  # utf-8-sig strips BOM automatically
                on_bad_lines='skip'  # Skip problematic lines
            )
            logger.info(f"Auto-detected delimiter successfully")
        except Exception as e:
            logger.warning(f"Auto-detection failed: {e}, trying semicolon delimiter")
            # Fallback to semicolon
            df = pd.read_csv(
                pd.io.common.BytesIO(file_content),
                header=0,
                sep=';',
                encoding='utf-8-sig',  # utf-8-sig strips BOM
                on_bad_lines='skip'
            )
        
        # Strip BOM from column names if present (extra safety)
        df.columns = df.columns.str.replace('^\ufeff', '', regex=True)
        
        # Convert all columns to string to avoid Delta Lake null type issues
        for col in df.columns:
            df[col] = df[col].astype(str)
        
        logger.info(f"Read {len(df)} rows with {len(df.columns)} columns")
        return df

