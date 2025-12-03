"""Silver V2 pipeline for fact_logement - Housing prices fact table (SQL-based)."""
from app.pipelines.silver_v2.base_v2 import SQLSilverV2Pipeline
from app.core.pipeline_registry import register_pipeline
import logging

logger = logging.getLogger(__name__)


@register_pipeline(
    layer="silver",
    name="logement",
    dependencies=["bronze.logement", "silver.geo"],
    description_fr="Table de faits des prix du logement par commune. Contient les loyers prédits, bornes d'intervalles et niveaux de qualité (normalisée sans duplication géographique)."
)
class FactLogementPipeline(SQLSilverV2Pipeline):
    """Transform logement data into normalized fact_logement fact table using SQL."""
    
    def get_name(self) -> str:
        return "silver_fact_logement"
    
    def get_target_table(self) -> str:
        return "logement"
    
    def get_sql_query(self) -> str:
        """SQL query to transform bronze logement data - FULLY NORMALIZED (no lib_* columns)."""
        return """
            WITH merged_data AS (
                SELECT *, LPAD(CAST(INSEE_C AS VARCHAR), 5, '0') AS INSEE_C_MERGED
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
                    -- Replace comma with period for decimal parsing
                    CAST(REPLACE(CAST(loypredm2 AS VARCHAR), ',', '.') AS DOUBLE) AS loypredm2_clean,
                    CAST(REPLACE(CAST("lwr.IPm2" AS VARCHAR), ',', '.') AS DOUBLE) AS lwr_clean,
                    CAST(REPLACE(CAST("upr.IPm2" AS VARCHAR), ',', '.') AS DOUBLE) AS upr_clean
                FROM merged_data
            ),
            with_row_number AS (
                SELECT *,
                    ROW_NUMBER() OVER (PARTITION BY code_commune ORDER BY ingestion_timestamp DESC) AS rn
                FROM with_code_commune
            )
            SELECT
                MD5(l.code_commune) AS logement_sk,
                c.commune_sk AS commune_sk,
                COALESCE(CAST(l.EPCI AS VARCHAR), '') AS epci_code,
                CAST(l.loypredm2_clean AS DECIMAL(10,2)) AS loyer_predicted_m2,
                CAST(l.lwr_clean AS DECIMAL(10,2)) AS loyer_lower_bound_m2,
                CAST(l.upr_clean AS DECIMAL(10,2)) AS loyer_upper_bound_m2,
                COALESCE(CAST(l.TYPPRED AS VARCHAR), '') AS prediction_level,
                '' AS data_rescued,
                SUBSTRING(l.code_commune, 1, 2) AS code_departement,
                COALESCE(CAST(l.REG AS VARCHAR), '') AS code_region,
                'silver_v2_fact_logement' AS job_insert_id,
                CURRENT_TIMESTAMP AS job_insert_date_utc,
                'silver_v2_fact_logement' AS job_modify_id,
                CURRENT_TIMESTAMP AS job_modify_date_utc
            FROM with_row_number l
            JOIN silver_geo c ON l.code_commune = c.commune_code
            WHERE rn = 1
              AND l.loypredm2_clean IS NOT NULL
              AND l.loypredm2_clean > 0
              AND l.lwr_clean IS NOT NULL
              AND l.upr_clean IS NOT NULL
              AND l.lwr_clean < l.upr_clean
        """
