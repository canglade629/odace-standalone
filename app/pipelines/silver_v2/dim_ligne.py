"""Silver V2 pipeline for dim_ligne - Railway lines dimension (SQL-based)."""
from app.pipelines.silver_v2.base_v2 import SQLSilverV2Pipeline
from app.core.pipeline_registry import register_pipeline
import logging

logger = logging.getLogger(__name__)


@register_pipeline(
    layer="silver_v2",
    name="dim_ligne",
    dependencies=["bronze.lignes"],
    description_fr="Table de dimension des lignes ferroviaires françaises avec tracés, catégories (TGV/classique) et points kilométriques."
)
class DimLignePipeline(SQLSilverV2Pipeline):
    """Transform lignes data into normalized dim_ligne dimension table using SQL."""
    
    def get_name(self) -> str:
        return "silver_v2_dim_ligne"
    
    def get_target_table(self) -> str:
        return "dim_ligne"
    
    def get_sql_query(self) -> str:
        """SQL query to transform bronze lignes data."""
        return """
            WITH deduplicated AS (
                SELECT *,
                    CASE WHEN catlig = 'Ligne à grande vitesse' THEN TRUE ELSE FALSE END AS is_tgv,
                    ROW_NUMBER() OVER (PARTITION BY code_ligne ORDER BY ingestion_timestamp DESC) AS rn
                FROM bronze_lignes
                WHERE code_ligne IS NOT NULL
            )
            SELECT 
                MD5(code_ligne) AS ligne_sk,
                code_ligne AS ligne_code,
                lib_ligne AS ligne_label,
                catlig AS categorie,
                is_tgv,
                CAST(rg_troncon AS INTEGER) AS rg_troncon,
                pkd, pkf, idgaia,
                x_d_l93, y_d_l93, x_f_l93, y_f_l93,
                x_d_wgs84, y_d_wgs84, x_f_wgs84, y_f_wgs84,
                c_geo_d, c_geo_f, geo_point, geo_shape, ingestion_timestamp,
                'silver_v2_dim_ligne' AS job_insert_id,
                CURRENT_TIMESTAMP AS job_insert_date_utc,
                'silver_v2_dim_ligne' AS job_modify_id,
                CURRENT_TIMESTAMP AS job_modify_date_utc
            FROM deduplicated
            WHERE rn = 1
        """
