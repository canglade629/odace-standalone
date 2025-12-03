"""Pipeline registry for managing and discovering pipelines."""
from typing import Dict, List, Type, Optional
from app.core.models import PipelineLayer, PipelineInfo
import logging

logger = logging.getLogger(__name__)


class PipelineRegistry:
    """Central registry for all data pipelines."""
    
    def __init__(self):
        self._pipelines: Dict[str, Dict[str, Type]] = {
            "bronze": {},
            "silver": {},
            "gold": {}
        }
        self._dependencies: Dict[str, List[str]] = {}
        self._descriptions_fr: Dict[str, str] = {}
    
    def register(
        self,
        layer: PipelineLayer,
        name: str,
        pipeline_class: Type,
        dependencies: Optional[List[str]] = None,
        description_fr: Optional[str] = None
    ):
        """
        Register a pipeline.
        
        Args:
            layer: Pipeline layer (bronze/silver/gold)
            name: Pipeline name
            pipeline_class: Pipeline class
            dependencies: List of pipeline names this pipeline depends on
            description_fr: French description of the pipeline
        """
        layer_str = layer.value if isinstance(layer, PipelineLayer) else layer
        
        if name in self._pipelines[layer_str]:
            logger.warning(f"Pipeline {layer_str}.{name} already registered, overwriting")
        
        self._pipelines[layer_str][name] = pipeline_class
        
        # Store dependencies
        full_name = f"{layer_str}.{name}"
        self._dependencies[full_name] = dependencies or []
        
        # Store French description
        if description_fr:
            self._descriptions_fr[full_name] = description_fr
        
        logger.info(f"Registered pipeline: {full_name}")
    
    def get(self, layer: PipelineLayer, name: str) -> Optional[Type]:
        """
        Get a pipeline class by layer and name.
        
        Args:
            layer: Pipeline layer
            name: Pipeline name
            
        Returns:
            Pipeline class or None if not found
        """
        layer_str = layer.value if isinstance(layer, PipelineLayer) else layer
        return self._pipelines.get(layer_str, {}).get(name)
    
    def list_pipelines(self, layer: Optional[PipelineLayer] = None) -> List[PipelineInfo]:
        """
        List all registered pipelines.
        
        Args:
            layer: Optional layer to filter by
            
        Returns:
            List of pipeline information
        """
        pipelines = []
        
        layers_to_check = [layer.value] if layer else ["bronze", "silver", "gold"]
        
        for layer_name in layers_to_check:
            for name, pipeline_class in self._pipelines[layer_name].items():
                full_name = f"{layer_name}.{name}"
                description = pipeline_class.__doc__
                if description:
                    description = description.strip().split('\n')[0]
                
                pipelines.append(PipelineInfo(
                    name=name,
                    layer=PipelineLayer(layer_name),
                    description=description,
                    description_fr=self._descriptions_fr.get(full_name),
                    dependencies=self._dependencies.get(full_name, [])
                ))
        
        return pipelines
    
    def get_dependencies(self, layer: PipelineLayer, name: str) -> List[str]:
        """
        Get dependencies for a pipeline.
        
        Args:
            layer: Pipeline layer
            name: Pipeline name
            
        Returns:
            List of dependency pipeline names (format: "layer.name")
        """
        layer_str = layer.value if isinstance(layer, PipelineLayer) else layer
        full_name = f"{layer_str}.{name}"
        return self._dependencies.get(full_name, [])


# Global registry instance
_registry = PipelineRegistry()


def get_registry() -> PipelineRegistry:
    """Get the global pipeline registry."""
    return _registry


def register_pipeline(layer: str, name: str, dependencies: Optional[List[str]] = None, description_fr: Optional[str] = None):
    """
    Decorator to register a pipeline class.
    
    Args:
        layer: Pipeline layer (bronze/silver/gold)
        name: Pipeline name
        dependencies: List of pipeline names this depends on (format: "layer.name")
        description_fr: French description of the pipeline
        
    Example:
        @register_pipeline(layer="bronze", name="accueillants")
        class BronzeAccueillantsPipeline(BaseBronzePipeline):
            pass
    """
    def decorator(cls):
        _registry.register(layer, name, cls, dependencies, description_fr)
        return cls
    return decorator


def register_pipelines_from_yaml(config_loader):
    """
    Register pipelines from YAML configuration files.
    
    Args:
        config_loader: ConfigLoader instance with pipeline configurations
    """
    logger.info("Loading pipelines from YAML configuration")
    
    configs = config_loader.load_all_configs()
    
    # Validate dependencies
    if not config_loader.validate_dependencies(configs):
        logger.warning("Some pipeline dependencies are invalid")
    
    # Register pipelines from all layers
    for layer, pipeline_configs in configs.items():
        for config in pipeline_configs:
            try:
                # Import the pipeline class
                pipeline_class = config_loader.get_pipeline_class(config.pipeline_class)
                
                # Register it
                _registry.register(
                    layer=layer,
                    name=config.name,
                    pipeline_class=pipeline_class,
                    dependencies=config.dependencies,
                    description_fr=config.description_fr
                )
                
                logger.info(f"Registered {layer}.{config.name} from YAML config")
                
            except Exception as e:
                logger.error(f"Failed to register pipeline {layer}.{config.name}: {e}", exc_info=True)

