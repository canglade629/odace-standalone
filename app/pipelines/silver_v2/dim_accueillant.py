"""Silver V2 pipeline for dim_accueillant - Host locations dimension (SQL-based)."""
from app.pipelines.silver_v2.base_v2 import SQLSilverV2Pipeline
from app.core.pipeline_registry import register_pipeline
import logging

logger = logging.getLogger(__name__)


@register_pipeline(
    layer="silver",
    name="accueillants",
    dependencies=["bronze.accueillants", "silver.geo"],
    description_fr="Table de dimension des structures d'accueil et organisations hôtes avec enrichissement géographique (commune_sk) via code postal."
)
class DimAccueillantPipeline(SQLSilverV2Pipeline):
    """Transform accueillants data into normalized dim_accueillant dimension table using SQL."""
    
    def get_name(self) -> str:
        return "silver_dim_accueillant"
    
    def get_target_table(self) -> str:
        return "accueillants"
    
    def get_sql_query(self) -> str:
        """SQL query to transform bronze accueillants data with geographic enrichment."""
        return """
            WITH accueillants_clean AS (
                SELECT 
                    COALESCE(statut, 'Sans statut') AS statut,
                    TRIM(Ville) AS ville,
                    TRIM(Code_postal) AS code_postal,
                    CAST(Latitude AS DOUBLE) AS latitude,
                    CAST(Longitude AS DOUBLE) AS longitude
                FROM bronze_accueillants
                WHERE Ville IS NOT NULL AND Ville != '' AND Ville != 'nan'
                  AND Latitude BETWEEN -90 AND 90
                  AND Longitude BETWEEN -180 AND 180
            ),
            deduplicated AS (
                SELECT 
                    a.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY latitude, longitude, statut, code_postal, UPPER(TRIM(ville))
                        ORDER BY ville
                    ) AS rn
                FROM accueillants_clean a
            ),
            with_commune AS (
                SELECT 
                    d.*,
                    c.commune_sk
                FROM deduplicated d
                LEFT JOIN silver_geo c
                    ON SUBSTRING(d.code_postal, 1, 5) = c.commune_code
                WHERE rn = 1
            )
            SELECT 
                MD5(CONCAT(CAST(latitude AS VARCHAR), CAST(longitude AS VARCHAR), statut, COALESCE(code_postal, ''), UPPER(ville))) AS accueillant_sk,
                commune_sk,
                statut,
                ville,
                code_postal,
                latitude,
                longitude,
                'silver_v2_dim_accueillant' AS job_insert_id,
                CURRENT_TIMESTAMP AS job_insert_date_utc,
                'silver_v2_dim_accueillant' AS job_modify_id,
                CURRENT_TIMESTAMP AS job_modify_date_utc
            FROM with_commune
        """
