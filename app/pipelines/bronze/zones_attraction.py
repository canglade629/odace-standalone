"""Bronze pipeline for zones attraction data."""
import pandas as pd
from app.pipelines.base import BaseBronzePipeline
from app.core.pipeline_registry import register_pipeline
import logging

logger = logging.getLogger(__name__)


@register_pipeline(layer="bronze", name="zones_attraction")
class BronzeZonesAttractionPipeline(BaseBronzePipeline):
    """Ingests zones d'attraction Excel data into bronze layer."""
    
    def get_name(self) -> str:
        return "bronze_zones_attraction"
    
    def get_source_path(self) -> str:
        return self.settings.get_raw_path("zones_attraction")
    
    def get_target_table(self) -> str:
        return "zones_attraction"
    
    def read_source_file(self, file_path: str) -> pd.DataFrame:
        """Read Excel file with specific sheet from GCS."""
        logger.info(f"Reading Excel file: {file_path}")
        
        # Download file to memory
        file_stream = self.gcs.download_to_stream(file_path)
        
        # Read Excel file: skip first 5 rows, then header on row 6
        df = pd.read_excel(
            file_stream,
            sheet_name="Composition_communale",
            skiprows=5,  # Skip first 5 rows
            header=0     # Row 6 becomes header
        )
        
        logger.info(f"Read {len(df)} rows with {len(df.columns)} columns from Composition_communale sheet")
        return df

