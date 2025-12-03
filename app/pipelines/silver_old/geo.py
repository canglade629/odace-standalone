"""Silver pipeline for geo data using SQL."""
from app.pipelines.base_sql import SQLSilverPipeline
from app.core.pipeline_registry import register_pipeline
import logging

logger = logging.getLogger(__name__)


@register_pipeline(
    layer="silver", 
    name="geo", 
    dependencies=["bronze.geo"],
    description_fr="Référentiel géographique des communes françaises avec codes INSEE et noms standardisés. Table de référence centrale pour tous les jointures géographiques."
)
class SilverGeoPipeline(SQLSilverPipeline):
    """Transform geo data for silver layer using SQL."""
    
    def get_name(self) -> str:
        return "silver_geo"
    
    def get_target_table(self) -> str:
        return "geo"
    
    def get_sql_query(self) -> str:
        """SQL query to transform bronze geo data."""
        return """
            SELECT 
                code_insee as CODGEO,
                nom_standard as LIBGEO
            FROM bronze_geo
        """

