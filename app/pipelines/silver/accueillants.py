"""Silver pipeline for accueillants data using SQL."""
from app.pipelines.base_sql import SQLSilverPipeline
from app.core.pipeline_registry import register_pipeline
import logging

logger = logging.getLogger(__name__)


@register_pipeline(layer="silver", name="accueillants", dependencies=["bronze.accueillants"])
class SilverAccueillantsPipeline(SQLSilverPipeline):
    """Transform accueillants data for silver layer using SQL."""
    
    def get_name(self) -> str:
        return "silver_accueillants"
    
    def get_target_table(self) -> str:
        return "accueillants"
    
    def get_sql_query(self) -> str:
        """SQL query to transform bronze accueillants data."""
        return """
            SELECT 
                COALESCE(statut, 'Sans statut') AS statut,
                Ville,
                Code_postal,
                Latitude,
                Longitude
            FROM bronze_accueillants
        """

