"""Silver pipeline for SIAE postes (job positions) data using SQL."""
from app.pipelines.base_sql import SQLSilverPipeline
from app.core.pipeline_registry import register_pipeline
import logging

logger = logging.getLogger(__name__)


@register_pipeline(
    layer="silver", 
    name="siae_postes", 
    dependencies=["bronze.siae_postes", "silver.siae_structures"],
    description_fr="Postes et offres d'emploi dans les SIAE. Détaille les types de contrats, codes ROME, et disponibilité des postes avec enrichissement géographique."
)
class SilverSIAEPostesPipeline(SQLSilverPipeline):
    """
    Transform SIAE job positions data for silver layer using SQL.
    
    Objectives:
    1. Link to structure for geographic context
    2. Clean job classification codes
    3. Standardize boolean and numeric fields
    4. Parse contract types
    """
    
    def get_name(self) -> str:
        return "silver_siae_postes"
    
    def get_target_table(self) -> str:
        return "siae_postes"
    
    def get_sql_query(self) -> str:
        """
        SQL query to transform bronze SIAE postes data.
        
        Joins with silver structures for geographic enrichment.
        """
        return """
            SELECT 
                p.id as poste_id,
                p.structure_id,
                p.structure_siret as siret,
                p.rome as rome_code,
                COALESCE(p.appellation_modifiee, '') as job_title,
                COALESCE(p.description, '') as job_description,
                COALESCE(p.type_contrat, '') as contract_type,
                CAST(p.recrutement_ouvert AS VARCHAR) as is_recruiting,
                COALESCE(CAST(p.nombre_postes_ouverts AS INTEGER), 0) as positions_available,
                p.cree_le as created_at,
                p.mis_a_jour_le as updated_at,
                -- Geographic context from structure
                s.city,
                s.postal_code,
                s.department,
                s.insee_code,
                s.structure_type,
                s.legal_name as structure_name
            FROM bronze_siae_postes p
            LEFT JOIN silver_siae_structures s ON p.structure_id = s.id
        """

