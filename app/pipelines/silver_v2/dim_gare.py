"""Silver V2 pipeline for dim_gare - Train stations dimension (SQL-based)."""
from app.pipelines.silver_v2.base_v2 import SQLSilverV2Pipeline
from app.core.pipeline_registry import register_pipeline
import logging

logger = logging.getLogger(__name__)


@register_pipeline(
    layer="silver",
    name="gares",
    dependencies=["bronze.gares", "silver.geo"],
    description_fr="Table de dimension des gares ferroviaires françaises avec codes UIC, services (fret/voyageurs) et enrichissement géographique."
)
class DimGarePipeline(SQLSilverV2Pipeline):
    """Transform gares data into normalized dim_gare dimension table using SQL."""
    
    def get_name(self) -> str:
        return "silver_dim_gare"
    
    def get_target_table(self) -> str:
        return "gares"
    
    def get_sql_query(self) -> str:
        """SQL query to transform bronze gares data with geographic enrichment."""
        return """
            WITH deduplicated AS (
                SELECT *,
                    ROW_NUMBER() OVER (PARTITION BY code_uic ORDER BY ingestion_timestamp DESC) AS rn
                FROM bronze_gares
                WHERE CAST(voyageurs AS VARCHAR) = 'O' OR CAST(voyageurs AS VARCHAR) = 'true' OR voyageurs = true
                  AND code_uic IS NOT NULL
            )
            SELECT 
                MD5(d.code_uic) AS gare_sk,
                COALESCE(CAST(c.commune_sk AS VARCHAR), '') AS commune_sk,
                COALESCE(CAST(d.code_uic AS VARCHAR), '') AS code_uic,
                COALESCE(CAST(d.libelle AS VARCHAR), '') AS libelle,
                CASE WHEN CAST(d.fret AS VARCHAR) IN ('O', 'true') OR d.fret = true THEN TRUE ELSE FALSE END AS fret,
                CASE WHEN CAST(d.voyageurs AS VARCHAR) IN ('O', 'true') OR d.voyageurs = true THEN TRUE ELSE FALSE END AS voyageurs,
                COALESCE(CAST(d.code_ligne AS VARCHAR), '') AS code_ligne,
                COALESCE(CAST(d.rg_troncon AS VARCHAR), '') AS rg_troncon,
                COALESCE(CAST(d.pk AS VARCHAR), '') AS pk,
                COALESCE(CAST(d.commune AS VARCHAR), '') AS commune,
                COALESCE(CAST(d.departemen AS VARCHAR), '') AS departement,
                COALESCE(CAST(d.idreseau AS VARCHAR), '') AS idreseau,
                COALESCE(CAST(d.idgaia AS VARCHAR), '') AS idgaia,
                COALESCE(CAST(d.x_l93 AS DOUBLE), 0.0) AS x_l93,
                COALESCE(CAST(d.y_l93 AS DOUBLE), 0.0) AS y_l93,
                COALESCE(CAST(d.x_wgs84 AS DOUBLE), 0.0) AS longitude,
                COALESCE(CAST(d.y_wgs84 AS DOUBLE), 0.0) AS latitude,
                COALESCE(CAST(d.c_geo AS VARCHAR), '') AS c_geo,
                COALESCE(CAST(d.geo_point AS VARCHAR), '') AS geo_point,
                COALESCE(CAST(d.geo_shape_coordinates AS VARCHAR), '') AS geo_shape_coordinates,
                COALESCE(CAST(d.geo_shape_type AS VARCHAR), '') AS geo_shape_type,
                CAST(d.ingestion_timestamp AS TIMESTAMP) AS ingestion_timestamp,
                'silver_v2_dim_gare' AS job_insert_id,
                CURRENT_TIMESTAMP AS job_insert_date_utc,
                'silver_v2_dim_gare' AS job_modify_id,
                CURRENT_TIMESTAMP AS job_modify_date_utc
            FROM deduplicated d
            LEFT JOIN silver_geo c ON d.c_geo = c.commune_code
            WHERE rn = 1
        """
