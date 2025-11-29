"""Pydantic models for API requests and responses."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class PipelineLayer(str, Enum):
    """Pipeline layer types."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


class PipelineStatus(str, Enum):
    """Pipeline execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class PipelineRunRequest(BaseModel):
    """Request to run a pipeline."""
    pipeline_name: str = Field(..., description="Name of the pipeline to run")
    layer: PipelineLayer = Field(..., description="Pipeline layer (bronze/silver/gold)")
    force: bool = Field(default=False, description="Force reprocessing of all files")


class FullPipelineRunRequest(BaseModel):
    """Request to run the full pipeline."""
    bronze_only: bool = Field(default=False, description="Run only bronze layer")
    silver_only: bool = Field(default=False, description="Run only silver layer")
    force: bool = Field(default=False, description="Force reprocessing")


class PipelineRunResponse(BaseModel):
    """Response for pipeline run."""
    run_id: str = Field(..., description="Unique run identifier")
    pipeline_name: str
    layer: PipelineLayer
    status: PipelineStatus
    started_at: datetime
    message: str = ""


class PipelineStatusResponse(BaseModel):
    """Response for pipeline status query."""
    run_id: str
    pipeline_name: str
    layer: PipelineLayer
    status: PipelineStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    message: str = ""
    error: Optional[str] = None
    stats: Optional[Dict[str, Any]] = None


class PipelineInfo(BaseModel):
    """Information about a registered pipeline."""
    name: str
    layer: PipelineLayer
    description: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)


class FileUploadResponse(BaseModel):
    """Response for file upload."""
    filename: str
    destination: str
    size_bytes: int
    uploaded_at: datetime


class PipelineListResponse(BaseModel):
    """List of available pipelines."""
    pipelines: List[PipelineInfo]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    timestamp: datetime
    version: str = "1.0.0"

