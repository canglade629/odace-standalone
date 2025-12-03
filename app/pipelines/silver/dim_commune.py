"""Silver pipeline for dim_commune - Geographic dimension table (SQL-based)."""
from app.pipelines.silver.base_v2 import SQLSilverV2Pipeline
from app.core.pipeline_registry import register_pipeline
import logging

logger = logging.getLogger(__name__)


@register_pipeline(
    layer="silver",
    name="dim_commune",
    dependencies=["bronze.geo"],
    description_fr="Table de dimension des communes françaises avec codes INSEE, départements et régions. Master Data Management (MDM) pour toutes les jointures géographiques."
)
class DimCommunePipeline(SQLSilverV2Pipeline):
    """Transform geo data into normalized dim_commune dimension table using SQL."""
    
    def get_name(self) -> str:
        return "dim_commune"
    
    def get_target_table(self) -> str:
        return "dim_commune"
    
    def get_sql_query(self) -> str:
        """
        SQL query to transform bronze geo data into dim_commune.
        
        Extracts:
        - commune_sk: Surrogate key (MD5 hash of INSEE code)
        - commune_code: INSEE code (5 digits)
        - commune_label: Official commune name
        - departement_code: Extracted from first 2-3 chars of INSEE code
        - region_code: Mapped from department code
        - 4 metadata columns
        
        Deduplicates by keeping only the latest record per code_insee.
        """
        return """
            WITH deduplicated AS (
                SELECT *,
                    ROW_NUMBER() OVER (PARTITION BY code_insee ORDER BY ingestion_timestamp DESC) AS rn
                FROM bronze_geo
                WHERE code_insee IS NOT NULL 
                  AND code_insee != 'nan'
                  AND code_insee != ''
            )
            SELECT 
                MD5(code_insee) as commune_sk,
                code_insee as commune_code,
                nom_standard as commune_label,
                CASE 
                    WHEN code_insee LIKE '97%' OR code_insee LIKE '98%' 
                    THEN SUBSTRING(code_insee, 1, 3)
                    ELSE SUBSTRING(code_insee, 1, 2)
                END as departement_code,
                CASE 
                    -- Auvergne-Rhône-Alpes (84)
                    WHEN SUBSTRING(code_insee, 1, 2) IN ('01','03','07','15','26','38','42','43','63','69','73','74') THEN '84'
                    -- Bourgogne-Franche-Comté (27)
                    WHEN SUBSTRING(code_insee, 1, 2) IN ('21','25','39','58','70','71','89','90') THEN '27'
                    -- Bretagne (53)
                    WHEN SUBSTRING(code_insee, 1, 2) IN ('22','29','35','56') THEN '53'
                    -- Centre-Val de Loire (24)
                    WHEN SUBSTRING(code_insee, 1, 2) IN ('18','28','36','37','41','45') THEN '24'
                    -- Corse (94)
                    WHEN SUBSTRING(code_insee, 1, 2) IN ('2A','2B','20') THEN '94'
                    -- Grand Est (44)
                    WHEN SUBSTRING(code_insee, 1, 2) IN ('08','10','51','52','54','55','57','67','68','88') THEN '44'
                    -- Hauts-de-France (32)
                    WHEN SUBSTRING(code_insee, 1, 2) IN ('02','59','60','62','80') THEN '32'
                    -- Île-de-France (11)
                    WHEN SUBSTRING(code_insee, 1, 2) IN ('75','77','78','91','92','93','94','95') THEN '11'
                    -- Normandie (28)
                    WHEN SUBSTRING(code_insee, 1, 2) IN ('14','27','50','61','76') THEN '28'
                    -- Nouvelle-Aquitaine (75)
                    WHEN SUBSTRING(code_insee, 1, 2) IN ('16','17','19','23','24','33','40','47','64','79','86','87') THEN '75'
                    -- Occitanie (76)
                    WHEN SUBSTRING(code_insee, 1, 2) IN ('09','11','12','30','31','32','34','46','48','65','66','81','82') THEN '76'
                    -- Pays de la Loire (52)
                    WHEN SUBSTRING(code_insee, 1, 2) IN ('44','49','53','72','85') THEN '52'
                    -- Provence-Alpes-Côte d'Azur (93)
                    WHEN SUBSTRING(code_insee, 1, 2) IN ('04','05','06','13','83','84') THEN '93'
                    -- Guadeloupe (01)
                    WHEN SUBSTRING(code_insee, 1, 3) = '971' THEN '01'
                    -- Martinique (02)
                    WHEN SUBSTRING(code_insee, 1, 3) = '972' THEN '02'
                    -- Guyane (03)
                    WHEN SUBSTRING(code_insee, 1, 3) = '973' THEN '03'
                    -- La Réunion (04)
                    WHEN SUBSTRING(code_insee, 1, 3) = '974' THEN '04'
                    -- Mayotte (06)
                    WHEN SUBSTRING(code_insee, 1, 3) = '976' THEN '06'
                    ELSE NULL
                END as region_code,
                'silver_geo' as job_insert_id,
                CURRENT_TIMESTAMP as job_insert_date_utc,
                'silver_geo' as job_modify_id,
                CURRENT_TIMESTAMP as job_modify_date_utc
            FROM deduplicated
            WHERE rn = 1
        """
