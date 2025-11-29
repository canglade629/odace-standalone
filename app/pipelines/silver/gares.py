"""Silver pipeline for gares data using SQL."""
from app.pipelines.base_sql import SQLSilverPipeline
from app.core.pipeline_registry import register_pipeline
import logging

logger = logging.getLogger(__name__)


@register_pipeline(layer="silver", name="gares", dependencies=["bronze.gares"])
class SilverGaresPipeline(SQLSilverPipeline):
    """Transform gares (train stations) data for silver layer using SQL."""
    
    def get_name(self) -> str:
        return "silver_gares"
    
    def get_target_table(self) -> str:
        return "gares"
    
    def get_sql_query(self) -> str:
        """SQL query to transform bronze gares data."""
        return """
            WITH deduplicated AS (
                SELECT *,
                    ROW_NUMBER() OVER (
                        PARTITION BY code_uic 
                        ORDER BY ingestion_timestamp DESC
                    ) AS rn
                FROM bronze_gares
                WHERE voyageurs = 'O'
            )
            SELECT 
                code_uic,
                libelle,
                fret,
                voyageurs,
                code_ligne,
                rg_troncon,
                pk,
                commune,
                departemen,
                idreseau,
                idgaia,
                x_l93,
                y_l93,
                x_wgs84 as longitude,
                y_wgs84 as latitude,
                c_geo,
                geo_point,
                geo_shape,
                ingestion_timestamp
            FROM deduplicated
            WHERE rn = 1
        """

