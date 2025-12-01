"""Silver pipeline for SIAE structures data using SQL."""
from app.pipelines.base_sql import SQLSilverPipeline
from app.core.pipeline_registry import register_pipeline
import logging

logger = logging.getLogger(__name__)


@register_pipeline(
    layer="silver", 
    name="siae_structures", 
    dependencies=["bronze.siae_structures", "bronze.geo"],
    description_fr="Structures d'insertion par l'activité économique (SIAE). Contient les informations légales, coordonnées et localisations géographiques des établissements."
)
class SilverSIAEStructuresPipeline(SQLSilverPipeline):
    """
    Transform SIAE structures data for silver layer using SQL.
    
    Objectives:
    1. Standardize addresses and contact information
    2. Map to INSEE codes by joining with geo data
    3. Remove nested postes field (handled in separate table)
    4. Clean and format fields
    5. Add geographic enrichment
    """
    
    def get_name(self) -> str:
        return "silver_siae_structures"
    
    def get_target_table(self) -> str:
        return "siae_structures"
    
    def get_sql_query(self) -> str:
        """
        SQL query to transform bronze SIAE structures data.
        
        Joins with geo data to enrich with INSEE codes.
        """
        return """
            SELECT 
                s.id,
                s.siret,
                s.type as structure_type,
                s.raison_sociale as legal_name,
                s.enseigne as trade_name,
                COALESCE(s.telephone, '') as phone,
                COALESCE(s.courriel, '') as email,
                COALESCE(s.site_web, '') as website,
                s.description,
                s.bloque_candidatures as accepting_applications,
                s.cree_le as created_at,
                s.mis_a_jour_le as updated_at,
                s.addresse_ligne_1 as address_line_1,
                COALESCE(s.addresse_ligne_2, '') as address_line_2,
                s.code_postal as postal_code,
                UPPER(TRIM(s.ville)) as city,
                s.departement as department,
                -- Try to match with geo data for INSEE code
                g.code_insee as insee_code,
                g.nom_standard as standardized_city_name
            FROM bronze_siae_structures s
            LEFT JOIN bronze_geo g 
                ON UPPER(TRIM(REPLACE(REPLACE(s.ville, '-', ' '), '  ', ' '))) = UPPER(TRIM(g.nom_standard))
                OR (
                    UPPER(TRIM(REPLACE(REPLACE(s.ville, '-', ' '), '  ', ' '))) LIKE UPPER(TRIM(g.nom_standard)) || '%'
                    AND LEFT(s.code_postal, 2) = LEFT(g.code_postal, 2)
                )
        """

