"""Configuration management using Pydantic Settings."""
import os
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""
    
    # GCP Configuration
    gcp_project_id: str = "icc-project-472009"
    gcs_bucket: str = "jaccueille"
    gcs_raw_prefix: str = "raw"
    gcs_delta_prefix: str = "delta"
    
    # API Configuration
    admin_secret: str = "changeme"
    environment: str = "development"
    
    # Optional Database URL for metadata
    database_url: Optional[str] = None
    
    # Application settings
    log_level: str = "INFO"
    
    # SIAE API Configuration
    siae_api_base_url: str = "https://emplois.inclusion.beta.gouv.fr/api/v1"
    siae_api_rate_limit: int = 12  # requests per minute
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def gcs_bucket_url(self) -> str:
        """Full GCS bucket URL."""
        return f"gs://{self.gcs_bucket}"
    
    @property
    def raw_path(self) -> str:
        """Path to raw data in GCS."""
        return f"{self.gcs_bucket_url}/{self.gcs_raw_prefix}"
    
    @property
    def delta_path(self) -> str:
        """Path to Delta tables in GCS."""
        return f"{self.gcs_bucket_url}/{self.gcs_delta_prefix}"
    
    def get_raw_path(self, domain: str) -> str:
        """Get path to raw data for a specific domain."""
        return f"{self.raw_path}/{domain}"
    
    def get_bronze_path(self, table: str) -> str:
        """Get path to bronze Delta table."""
        return f"{self.delta_path}/bronze/{table}"
    
    def get_silver_path(self, table: str) -> str:
        """Get path to silver Delta table."""
        return f"{self.delta_path}/silver/{table}"
    
    def get_gold_path(self, table: str) -> str:
        """Get path to gold Delta table."""
        return f"{self.delta_path}/gold/{table}"
    
    def get_checkpoint_path(self) -> str:
        """Get path to checkpoint Delta table."""
        return f"{self.delta_path}/checkpoints"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

