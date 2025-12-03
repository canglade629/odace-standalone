"""Silver pipeline for dim_accueillant - Host locations dimension (SQL-based)."""
from app.pipelines.silver.base_v2 import SQLSilverV2Pipeline
from app.core.pipeline_registry import register_pipeline
import logging

logger = logging.getLogger(__name__)


@register_pipeline(
    layer="silver",
    name="dim_accueillant",
    dependencies=["bronze.accueillants", "silver.dim_commune"],
    description_fr="Table de dimension des structures d'accueil avec enrichissement géographique (FK vers dim_commune) et coordonnées GPS."
)
class DimAccueillantPipeline(SQLSilverV2Pipeline):
    """Transform accueillants data into normalized dim_accueillant dimension table using SQL."""
    
    def get_name(self) -> str:
        return "dim_accueillant"
    
    def get_target_table(self) -> str:
        return "dim_accueillant"
    
    def get_sql_query(self) -> str:
        """SQL query to transform bronze accueillants data with geographic enrichment and deduplication."""
        return """
            WITH deduplicated_bronze AS (
                SELECT *,
                    ROW_NUMBER() OVER (
                        PARTITION BY TRIM(Ville), TRIM(Code_postal), CAST(Latitude AS DOUBLE), CAST(Longitude AS DOUBLE), statut
                        ORDER BY ingestion_timestamp DESC
                    ) AS rn
                FROM bronze_accueillants
                WHERE Ville IS NOT NULL AND Ville != '' AND Ville != 'nan'
            ),
            accueillants_clean AS (
                SELECT 
                    COALESCE(statut, 'Sans statut') AS statut,
                    TRIM(Ville) AS ville,
                    TRIM(Code_postal) AS code_postal,
                    CAST(Latitude AS DOUBLE) AS latitude,
                    CAST(Longitude AS DOUBLE) AS longitude
                FROM deduplicated_bronze
                WHERE rn = 1
                  AND Latitude BETWEEN -90 AND 90
                  AND Longitude BETWEEN -180 AND 180
            ),
            with_commune AS (
                SELECT 
                    a.*,
                    c.commune_sk
                FROM accueillants_clean a
                LEFT JOIN silver_dim_commune c
                    ON SUBSTRING(a.code_postal, 1, 5) = c.commune_code
            )
            SELECT 
                MD5(CONCAT(CAST(latitude AS VARCHAR), CAST(longitude AS VARCHAR), statut, COALESCE(code_postal, ''), UPPER(ville))) AS accueillant_sk,
                commune_sk,
                statut,
                ville,
                code_postal,
                latitude,
                longitude,
                'dim_accueillant' AS job_insert_id,
                CURRENT_TIMESTAMP AS job_insert_date_utc,
                'dim_accueillant' AS job_modify_id,
                CURRENT_TIMESTAMP AS job_modify_date_utc
            FROM with_commune
        """
