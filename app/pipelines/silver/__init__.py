"""Silver layer pipelines."""
from app.pipelines.silver.accueillants import SilverAccueillantsPipeline
from app.pipelines.silver.geo import SilverGeoPipeline
from app.pipelines.silver.gares import SilverGaresPipeline
from app.pipelines.silver.lignes import SilverLignesPipeline
from app.pipelines.silver.logement import SilverLogementPipeline
from app.pipelines.silver.zones_attraction import SilverZonesAttractionPipeline
from app.pipelines.silver.siae_structures import SilverSIAEStructuresPipeline
from app.pipelines.silver.siae_postes import SilverSIAEPostesPipeline

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

