"""Silver pipeline for zones attraction data using SQL."""
from app.pipelines.base_sql import SQLSilverPipeline
from app.core.pipeline_registry import register_pipeline
import logging

logger = logging.getLogger(__name__)


@register_pipeline(
    layer="silver", 
    name="zones_attraction", 
    dependencies=["bronze.zones_attraction", "silver.geo"],
    description_fr="Aires d'attraction des villes 2020. Définis les zones d'influence économique des pôles urbains et leurs communes rattachées."
)
class SilverZonesAttractionPipeline(SQLSilverPipeline):
    """Transform zones attraction data with complex text processing and joins using SQL."""
    
    def get_name(self) -> str:
        return "silver_zones_attraction"
    
    def get_target_table(self) -> str:
        return "zones_attraction"
    
    def get_sql_query(self) -> str:
        """SQL query to transform bronze zones attraction data."""
        return """
            WITH cleaned_bronze AS (
                SELECT
                    CODGEO,
                    LIBGEO,
                    AAV2020,
                    REGEXP_REPLACE(LIBAAV2020, '(?i)\\s*\\(partie française\\)', '') AS LIBAAV2020_CLEAN,
                    LIBAAV2020,
                    CATEAAV2020,
                    DEP,
                    REG
                FROM bronze_zones_attraction
                WHERE AAV2020 != '000'
            ),
            exploded_bronze AS (
                SELECT
                    CODGEO,
                    LIBGEO,
                    AAV2020,
                    TRIM(value) AS LIBAAV2020_CLEAN,
                    CATEAAV2020,
                    DEP,
                    REG
                FROM cleaned_bronze,
                LATERAL (SELECT UNNEST(STRING_SPLIT(LIBAAV2020_CLEAN, ' - ')) AS value)
            ),
            name_cleaned AS (
                SELECT
                    CODGEO,
                    LIBGEO,
                    AAV2020,
                    CASE 
                        WHEN REPLACE(LIBAAV2020_CLEAN, 'œ', 'oe') ILIKE 'Hesdin%' THEN 'Hesdin'
                        WHEN REPLACE(LIBAAV2020_CLEAN, 'œ', 'oe') ILIKE 'Cugand%' THEN 'Cugand'
                        ELSE REPLACE(LIBAAV2020_CLEAN, 'œ', 'oe')
                    END AS LIBAAV2020,
                    CATEAAV2020,
                    DEP,
                    REG
                FROM exploded_bronze
            )
            SELECT 
                b.CODGEO AS CODGEO,
                b.LIBGEO AS LIBGEO,
                b.AAV2020 AS CODEAAV,
                g.CODGEO AS CODGEOAAV,
                b.LIBAAV2020,
                b.CATEAAV2020 AS CATEAAV,
                b.DEP,
                b.REG
            FROM name_cleaned b
            INNER JOIN silver_geo g
                ON REGEXP_REPLACE(UPPER(b.LIBAAV2020), '[^A-Z0-9]', '') = 
                   REGEXP_REPLACE(UPPER(REPLACE(g.LIBGEO, 'œ', 'oe')), '[^A-Z0-9]', '')
            WHERE b.CODGEO NOT LIKE CONCAT('%', g.CODGEO, '%')
        """

