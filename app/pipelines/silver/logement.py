"""Silver pipeline for logement data using SQL."""
from app.pipelines.base_sql import SQLSilverPipeline
from app.core.pipeline_registry import register_pipeline
import logging

logger = logging.getLogger(__name__)


@register_pipeline(
    layer="silver", 
    name="logement", 
    dependencies=["bronze.logement"],
    description_fr="Données de prix et statistiques du logement par commune. Inclut les loyers moyens, bornes de prédiction et niveaux de qualité des estimations."
)
class SilverLogementPipeline(SQLSilverPipeline):
    """Transform logement (housing) data for silver layer using SQL."""
    
    def get_name(self) -> str:
        return "silver_logement"
    
    def get_target_table(self) -> str:
        return "logement"
    
    def get_sql_query(self) -> str:
        """SQL query to transform bronze logement data - EXACT match to Databricks logic."""
        return """
            WITH merged_data AS (
                SELECT *,
                    LPAD(INSEE_C, 5, '0') AS INSEE_C_MERGED
                FROM bronze_logement
            ),
            with_code_commune AS (
                SELECT *,
                    CASE
                        WHEN INSEE_C_MERGED LIKE '132%' THEN '13055'
                        WHEN INSEE_C_MERGED LIKE '693%' THEN '69123'
                        WHEN INSEE_C_MERGED LIKE '751%' THEN '75056'
                        ELSE INSEE_C_MERGED
                    END AS code_commune,
                    CASE
                        WHEN INSEE_C_MERGED LIKE '132%' THEN '13055'
                        WHEN INSEE_C_MERGED LIKE '693%' THEN '69300'
                        WHEN INSEE_C_MERGED LIKE '751%' THEN '75056'
                        ELSE INSEE_C_MERGED
                    END AS partition_key
                FROM merged_data
            ),
            with_row_number AS (
                SELECT *,
                    ROW_NUMBER() OVER (
                        PARTITION BY partition_key
                        ORDER BY ingestion_timestamp DESC
                    ) AS rn
                FROM with_code_commune
            )
            SELECT
                code_commune,
                LIBGEO AS lib_commune,
                EPCI AS lib_epci,
                DEP AS lib_dep,
                CAST(REG AS VARCHAR) AS lib_reg,
                loypredm2 AS prix_loyer,
                "lwr.IPm2" AS borne_inf_pred,
                "upr.IPm2" AS borne_sup_pred,
                TYPPRED AS niveau_pred,
                '' AS rescued_data
            FROM with_row_number
            WHERE rn = 1
        """

