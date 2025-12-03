"""Bronze layer pipelines."""
from app.pipelines.bronze.accueillants import BronzeAccueillantsPipeline
from app.pipelines.bronze.geo import BronzeGeoPipeline
from app.pipelines.bronze.logement import BronzeLogementPipeline
from app.pipelines.bronze.transport import BronzeGaresPipeline, BronzeLignesPipeline
from app.pipelines.bronze.zones_attraction import BronzeZonesAttractionPipeline
from app.pipelines.bronze.siae_structures import BronzeSIAEStructuresPipeline
from app.pipelines.bronze.siae_postes import BronzeSIAEPostesPipeline
from app.pipelines.bronze.open_data import BronzeOpenDataPipeline

__all__ = [
    "BronzeAccueillantsPipeline",
    "BronzeGeoPipeline",
    "BronzeLogementPipeline",
    "BronzeGaresPipeline",
    "BronzeLignesPipeline",
    "BronzeZonesAttractionPipeline",
    "BronzeSIAEStructuresPipeline",
    "BronzeSIAEPostesPipeline",
    "BronzeOpenDataPipeline",
]

