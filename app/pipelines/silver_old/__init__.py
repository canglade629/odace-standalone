"""Silver layer pipelines - Now using V2 implementations."""
# Import from silver_v2 but expose as silver layer for backward compatibility
from app.pipelines.silver_v2.dim_commune import DimCommunePipeline as SilverGeoPipeline
from app.pipelines.silver_v2.dim_accueillant import DimAccueillantPipeline as SilverAccueillantsPipeline
from app.pipelines.silver_v2.dim_gare import DimGarePipeline as SilverGaresPipeline
from app.pipelines.silver_v2.dim_ligne import DimLignePipeline as SilverLignesPipeline
from app.pipelines.silver_v2.dim_siae_structure import DimSIAEStructurePipeline as SilverSIAEStructuresPipeline
from app.pipelines.silver_v2.fact_logement import FactLogementPipeline as SilverLogementPipeline
from app.pipelines.silver_v2.fact_zone_attraction import FactZoneAttractionPipeline as SilverZonesAttractionPipeline
from app.pipelines.silver_v2.fact_siae_poste import FactSIAEPostePipeline as SilverSIAEPostesPipeline

__all__ = [
    "SilverAccueillantsPipeline",
    "SilverGeoPipeline",
    "SilverGaresPipeline",
    "SilverLignesPipeline",
    "SilverLogementPipeline",
    "SilverZonesAttractionPipeline",
    "SilverSIAEStructuresPipeline",
    "SilverSIAEPostesPipeline",
]

