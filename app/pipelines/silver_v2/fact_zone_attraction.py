"""Silver V2 pipeline for fact_zone_attraction - Urban attraction zones fact table (SQL-based)."""
from app.pipelines.silver_v2.base_v2 import SQLSilverV2Pipeline
from app.core.pipeline_registry import register_pipeline
import logging

logger = logging.getLogger(__name__)


@register_pipeline(
    layer="silver_v2",
    name="fact_zone_attraction",
    dependencies=["bronze.zones_attraction", "silver_v2.dim_commune"],
    description_fr="Table de faits des aires d'attraction des villes 2020 avec FKs vers communes (commune et pôle) et catégories d'attraction."
)
class FactZoneAttractionPipeline(SQLSilverV2Pipeline):
    """Transform zones_attraction data into normalized fact_zone_attraction fact table using SQL."""
    
    def get_name(self) -> str:
        return "silver_v2_fact_zone_attraction"
    
    def get_target_table(self) -> str:
        return "fact_zone_attraction"
    
    def get_sql_query(self) -> str:
        """SQL query to transform bronze zones_attraction data with dual FK enrichment."""
        return """
            WITH cleaned_bronze AS (
                SELECT
                    CODGEO, LIBGEO, AAV2020,
                    REGEXP_REPLACE(LIBAAV2020, '(?i)\\\\s*\\\\(partie française\\\\)', '') AS LIBAAV2020_CLEAN,
                    CATEAAV2020, DEP, REG
                FROM bronze_zones_attraction
                WHERE AAV2020 != '000' AND CODGEO IS NOT NULL
            ),
            name_cleaned AS (
                SELECT
                    CODGEO, LIBGEO, AAV2020,
                    CASE 
                        WHEN REPLACE(LIBAAV2020_CLEAN, 'œ', 'oe') ILIKE 'Hesdin%' THEN 'Hesdin'
                        WHEN REPLACE(LIBAAV2020_CLEAN, 'œ', 'oe') ILIKE 'Cugand%' THEN 'Cugand'
                        ELSE REPLACE(LIBAAV2020_CLEAN, 'œ', 'oe')
                    END AS LIBAAV2020,
                    CATEAAV2020, DEP, REG
                FROM cleaned_bronze
            ),
            with_pole_match AS (
                SELECT 
                    b.CODGEO, b.AAV2020 AS CODEAAV,
                    c_pole.commune_code AS CODGEOAAV,
                    b.LIBAAV2020,
                    b.CATEAAV2020 AS CATEAAV,
                    b.DEP, b.REG
                FROM name_cleaned b
                INNER JOIN silver_v2_dim_commune c_pole
                    ON REGEXP_REPLACE(UPPER(b.LIBAAV2020), '[^A-Z0-9]', '') = 
                       REGEXP_REPLACE(UPPER(REPLACE(c_pole.commune_label, 'œ', 'oe')), '[^A-Z0-9]', '')
                WHERE b.CODGEO NOT LIKE CONCAT('%', c_pole.commune_code, '%')
            )
            SELECT 
                MD5(CONCAT(z.CODGEO, z.CODEAAV, z.CODGEOAAV)) AS zone_attraction_sk,
                c1.commune_sk,
                c2.commune_sk AS commune_pole_sk,
                z.CODEAAV AS aire_attraction_code,
                z.LIBAAV2020 AS aire_attraction_label,
                z.CATEAAV AS aire_attraction_categorie,
                z.DEP AS departement_code,
                z.REG AS region_code,
                'silver_v2_fact_zone_attraction' AS job_insert_id,
                CURRENT_TIMESTAMP AS job_insert_date_utc,
                'silver_v2_fact_zone_attraction' AS job_modify_id,
                CURRENT_TIMESTAMP AS job_modify_date_utc
            FROM with_pole_match z
            JOIN silver_v2_dim_commune c1 ON z.CODGEO = c1.commune_code
            JOIN silver_v2_dim_commune c2 ON z.CODGEOAAV = c2.commune_code
        """
