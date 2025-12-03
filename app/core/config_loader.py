"""Configuration loader for pipeline YAML files."""
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from importlib import import_module

logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for a single pipeline."""
    name: str
    target_table: str
    pipeline_class: str
    description: Optional[str] = None
    description_fr: Optional[str] = None
    dependencies: Optional[List[str]] = None
    source_path: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: dict) -> "PipelineConfig":
        """Create PipelineConfig from dictionary."""
        return cls(
            name=data["name"],
            target_table=data["target_table"],
            pipeline_class=data["pipeline_class"],
            description=data.get("description"),
            description_fr=data.get("description_fr"),
            dependencies=data.get("dependencies", []),
            source_path=data.get("source_path")
        )


class ConfigLoader:
    """Loads and validates pipeline configurations from YAML files."""
    
    def __init__(self, config_dir: str = "config/pipelines"):
        """
        Initialize the config loader.
        
        Args:
            config_dir: Directory containing pipeline YAML files
        """
        self.config_dir = Path(config_dir)
        self._cache: Dict[str, List[PipelineConfig]] = {}
    
    def load_layer_config(self, layer: str) -> List[PipelineConfig]:
        """
        Load pipeline configurations for a specific layer.
        
        Args:
            layer: Layer name (bronze, silver, gold)
            
        Returns:
            List of PipelineConfig objects
        """
        # Check cache first
        if layer in self._cache:
            logger.debug(f"Returning cached config for {layer}")
            return self._cache[layer]
        
        config_file = self.config_dir / f"{layer}.yaml"
        
        if not config_file.exists():
            logger.warning(f"Config file not found: {config_file}")
            return []
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            if not data or "pipelines" not in data:
                logger.warning(f"No pipelines found in {config_file}")
                return []
            
            pipelines = []
            for pipeline_data in data["pipelines"]:
                try:
                    config = PipelineConfig.from_dict(pipeline_data)
                    pipelines.append(config)
                    logger.debug(f"Loaded config for {layer}.{config.name}")
                except Exception as e:
                    logger.error(f"Error parsing pipeline config: {e}", exc_info=True)
                    logger.error(f"Pipeline data: {pipeline_data}")
                    continue
            
            # Cache the results
            self._cache[layer] = pipelines
            logger.info(f"Loaded {len(pipelines)} pipeline configs for {layer} layer")
            
            return pipelines
            
        except Exception as e:
            logger.error(f"Error loading config file {config_file}: {e}", exc_info=True)
            return []
    
    def load_all_configs(self) -> Dict[str, List[PipelineConfig]]:
        """
        Load all pipeline configurations for all layers.
        
        Returns:
            Dictionary mapping layer names to lists of PipelineConfig
        """
        configs = {}
        for layer in ["bronze", "silver", "gold"]:
            configs[layer] = self.load_layer_config(layer)
        return configs
    
    def get_pipeline_class(self, pipeline_class_path: str):
        """
        Dynamically import and return a pipeline class.
        
        Args:
            pipeline_class_path: Full path to class (e.g., "app.pipelines.bronze.geo.BronzeGeoPipeline")
            
        Returns:
            The pipeline class
        """
        try:
            module_path, class_name = pipeline_class_path.rsplit('.', 1)
            module = import_module(module_path)
            pipeline_class = getattr(module, class_name)
            logger.debug(f"Successfully imported {pipeline_class_path}")
            return pipeline_class
        except Exception as e:
            logger.error(f"Error importing pipeline class {pipeline_class_path}: {e}")
            raise
    
    def validate_dependencies(self, configs: Dict[str, List[PipelineConfig]]) -> bool:
        """
        Validate that all pipeline dependencies exist.
        
        Args:
            configs: Dictionary of layer configs
            
        Returns:
            True if all dependencies are valid
        """
        # Build a set of all available pipelines
        available = set()
        for layer, pipeline_list in configs.items():
            for pipeline in pipeline_list:
                available.add(f"{layer}.{pipeline.name}")
        
        # Check all dependencies
        all_valid = True
        for layer, pipeline_list in configs.items():
            for pipeline in pipeline_list:
                if pipeline.dependencies:
                    for dep in pipeline.dependencies:
                        if dep not in available:
                            logger.error(
                                f"Pipeline {layer}.{pipeline.name} depends on {dep}, "
                                f"but {dep} is not found in configuration"
                            )
                            all_valid = False
        
        return all_valid
    
    def clear_cache(self):
        """Clear the configuration cache."""
        self._cache.clear()
        logger.debug("Configuration cache cleared")


# Global instance
_config_loader = None


def get_config_loader(config_dir: str = "config/pipelines") -> ConfigLoader:
    """Get the global config loader instance."""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader(config_dir)
    return _config_loader

