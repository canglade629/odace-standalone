"""Bronze pipeline for accueillants data."""
import pandas as pd
import io
from app.pipelines.base import BaseBronzePipeline
from app.core.pipeline_registry import register_pipeline
import logging

logger = logging.getLogger(__name__)


@register_pipeline(layer="bronze", name="accueillants")
class BronzeAccueillantsPipeline(BaseBronzePipeline):
    """Ingests accueillants Excel data into bronze layer."""
    
    def get_name(self) -> str:
        return "bronze_accueillants"
    
    def get_source_path(self) -> str:
        return self.settings.get_raw_path("accueillants")
    
    def get_target_table(self) -> str:
        return "accueillants"
    
    def read_source_file(self, file_path: str) -> pd.DataFrame:
        """Read Excel file from GCS."""
        logger.info(f"Reading Excel file: {file_path}")
        
        # Download file to memory
        file_stream = self.gcs.download_to_stream(file_path)
        
        # Read Excel file (header is first row)
        df = pd.read_excel(file_stream, header=0)
        
        # Rename columns to replace spaces with underscores
        new_columns = {col: col.replace(' ', '_') for col in df.columns}
        df.rename(columns=new_columns, inplace=True)
        
        logger.info(f"Read {len(df)} rows with {len(df.columns)} columns")
        return df

