"""Silver V2 pipeline for dim_siae_structure - SIAE structures dimension (SQL-based)."""
from app.pipelines.silver_v2.base_v2 import SQLSilverV2Pipeline
from app.core.pipeline_registry import register_pipeline
import logging

logger = logging.getLogger(__name__)


@register_pipeline(
    layer="silver",
    name="siae_structures",
    dependencies=["bronze.siae_structures", "bronze.geo", "silver.geo"],
    description_fr="Table de dimension des structures d'insertion par l'activité économique (SIAE) avec informations légales et enrichissement géographique."
)
class DimSIAEStructurePipeline(SQLSilverV2Pipeline):
    """Transform SIAE structures data into normalized dim_siae_structure dimension table using SQL."""
    
    def get_name(self) -> str:
        return "silver_siae_structures"
    
    def get_target_table(self) -> str:
        return "siae_structures"
    
    def get_sql_query(self) -> str:
        """SQL query to transform bronze SIAE structures data with geographic enrichment."""
        return """
            WITH geo_enriched AS (
                SELECT s.*, g.code_insee, g.nom_standard
                FROM bronze_siae_structures s
                LEFT JOIN bronze_geo g 
                    ON UPPER(TRIM(REPLACE(s.ville, '-', ' '))) = UPPER(TRIM(g.nom_standard))
            ),
            with_commune_sk AS (
                SELECT s.*, c.commune_sk
                FROM geo_enriched s
                LEFT JOIN silver_geo c ON s.code_insee = c.commune_code
            ),
            deduplicated AS (
                SELECT *,
                    ROW_NUMBER() OVER (
                        PARTITION BY siret 
                        ORDER BY CASE WHEN commune_sk IS NOT NULL THEN 0 ELSE 1 END, 
                                 mis_a_jour_le DESC
                    ) AS rn
                FROM with_commune_sk
                WHERE LENGTH(REGEXP_REPLACE(siret, '[^0-9]', '')) = 14
            )
            SELECT 
                MD5(siret) AS siae_structure_sk,
                commune_sk, id, siret, type AS structure_type,
                raison_sociale, enseigne, 
                COALESCE(telephone, '') AS telephone,
                COALESCE(courriel, '') AS courriel,
                COALESCE(site_web, '') AS site_web,
                description,
                CASE WHEN bloque_candidatures = TRUE THEN FALSE ELSE TRUE END AS accepte_candidatures,
                cree_le AS date_creation,
                mis_a_jour_le AS date_mise_a_jour,
                addresse_ligne_1 AS adresse_ligne1,
                COALESCE(addresse_ligne_2, '') AS adresse_ligne2,
                code_postal, ville, departement, code_insee,
                nom_standard AS ville_standardisee,
                'silver_siae_structures' AS job_insert_id,
                CURRENT_TIMESTAMP AS job_insert_date_utc,
                'silver_siae_structures' AS job_modify_id,
                CURRENT_TIMESTAMP AS job_modify_date_utc
            FROM deduplicated
            WHERE rn = 1
        """
