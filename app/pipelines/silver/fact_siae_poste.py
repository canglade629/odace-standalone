"""Silver pipeline for fact_siae_poste - SIAE job positions fact table (SQL-based)."""
from app.pipelines.silver.base_v2 import SQLSilverV2Pipeline
from app.core.pipeline_registry import register_pipeline
import logging

logger = logging.getLogger(__name__)


@register_pipeline(
    layer="silver",
    name="fact_siae_poste",
    dependencies=["bronze.siae_postes", "silver.dim_siae_structure"],
    description_fr="Table de faits des postes ouverts en SIAE avec codes ROME, types de contrats et disponibilité. FK vers dim_siae_structure."
)
class FactSIAEPostePipeline(SQLSilverV2Pipeline):
    """Transform SIAE postes data into normalized fact_siae_poste fact table using SQL."""
    
    def get_name(self) -> str:
        return "fact_siae_poste"
    
    def get_target_table(self) -> str:
        return "fact_siae_poste"
    
    def get_sql_query(self) -> str:
        """SQL query to transform bronze SIAE postes data with structure FK and deduplication."""
        return """
            WITH postes_with_rome AS (
                SELECT 
                    p.*,
                    -- Extract ROME code from parentheses e.g. "Agent (K2503)" -> "K2503"
                    REGEXP_EXTRACT(p.rome, '\\(([A-Z][0-9]{4})\\)', 1) AS rome_code_extracted
                FROM bronze_siae_postes p
                WHERE p.rome IS NOT NULL 
                  AND p.rome LIKE '%(%)%'
            ),
            deduplicated AS (
                SELECT *,
                    ROW_NUMBER() OVER (
                        PARTITION BY id, structure_id 
                        ORDER BY mis_a_jour_le DESC, ingestion_timestamp DESC
                    ) AS rn
                FROM postes_with_rome
            )
            SELECT 
                MD5(CONCAT(CAST(p.id AS VARCHAR), CAST(p.structure_id AS VARCHAR))) AS siae_poste_sk,
                COALESCE(s.siae_structure_sk, '') AS siae_structure_sk,
                CAST(p.id AS VARCHAR) AS poste_id,
                CAST(p.structure_id AS VARCHAR) AS structure_id,
                COALESCE(CAST(p.structure_siret AS VARCHAR), '') AS structure_siret,
                COALESCE(p.rome_code_extracted, '') AS rome_code,
                COALESCE(CAST(p.appellation_modifiee AS VARCHAR), p.rome) AS intitule_poste,
                COALESCE(CAST(p.description AS VARCHAR), '') AS description_poste,
                COALESCE(CAST(p.type_contrat AS VARCHAR), '') AS contrat_type,
                CASE 
                    WHEN CAST(p.recrutement_ouvert AS VARCHAR) IN ('true', 'True', '1', 't') THEN TRUE 
                    ELSE FALSE 
                END AS poste_disponible,
                COALESCE(CAST(p.nombre_postes_ouverts AS INTEGER), 0) AS postes_nombre,
                CAST(p.cree_le AS TIMESTAMP) AS creation_date_utc,
                CAST(p.mis_a_jour_le AS TIMESTAMP) AS modification_date_utc,
                'fact_siae_poste' AS job_insert_id,
                CURRENT_TIMESTAMP AS job_insert_date_utc,
                'fact_siae_poste' AS job_modify_id,
                CURRENT_TIMESTAMP AS job_modify_date_utc
            FROM deduplicated p
            LEFT JOIN silver_dim_siae_structure s ON CAST(p.structure_id AS VARCHAR) = CAST(s.id AS VARCHAR)
            WHERE p.rn = 1 AND p.rome_code_extracted IS NOT NULL
        """
