"""Silver pipeline for lignes data using SQL."""
from app.pipelines.base_sql import SQLSilverPipeline
from app.core.pipeline_registry import register_pipeline
import logging

logger = logging.getLogger(__name__)


@register_pipeline(
    layer="silver", 
    name="lignes", 
    dependencies=["bronze.lignes"],
    description_fr="Référentiel des lignes ferroviaires françaises. Inclut les tracés, catégories (TGV/classique), et points kilométriques de début et fin."
)
class SilverLignesPipeline(SQLSilverPipeline):
    """Transform lignes (train lines) data for silver layer using SQL."""
    
    def get_name(self) -> str:
        return "silver_lignes"
    
    def get_target_table(self) -> str:
        return "lignes"
    
    def get_sql_query(self) -> str:
        """SQL query to transform bronze lignes data."""
        return """
            WITH deduplicated AS (
                SELECT *,
                    CASE 
                        WHEN catlig = 'Ligne à grande vitesse' THEN '1' 
                        ELSE '0' 
                    END AS isTGV,
                    ROW_NUMBER() OVER (
                        PARTITION BY code_ligne 
                        ORDER BY ingestion_timestamp DESC
                    ) AS rn
                FROM bronze_lignes
            )
            SELECT 
                code_ligne,
                lib_ligne,
                catlig,
                isTGV,
                CAST(rg_troncon AS INTEGER) as rg_troncon,
                pkd,
                pkf,
                idgaia,
                x_d_l93,
                y_d_l93,
                x_f_l93,
                y_f_l93,
                x_d_wgs84,
                y_d_wgs84,
                x_f_wgs84,
                y_f_wgs84,
                c_geo_d,
                c_geo_f,
                geo_point,
                geo_shape,
                ingestion_timestamp
            FROM deduplicated
            WHERE rn = 1
        """

