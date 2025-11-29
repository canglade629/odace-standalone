"""Pipeline orchestration endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.auth import verify_api_key
from app.core.models import (
    FullPipelineRunRequest,
    PipelineRunResponse,
    PipelineStatusResponse,
    PipelineListResponse,
    PipelineLayer,
    PipelineStatus
)
from app.core.pipeline_executor import get_pipeline_executor
from app.core.pipeline_registry import get_registry
from app.core.rate_limiter import limiter
from datetime import datetime
import uuid

router = APIRouter(prefix="/api/pipeline", tags=["pipeline"])


@router.post("/run")
@limiter.limit("60/minute")
async def run_full_pipeline(
    request: Request,
    pipeline_request: FullPipelineRunRequest = FullPipelineRunRequest(),
    user_id: str = Depends(verify_api_key)
):
    """
    Run the full data pipeline (bronze → silver).
    
    Args:
        request: Pipeline run configuration
        user_id: User ID from API key authentication
        
    Returns:
        Summary of pipeline execution including job ID
    """
    executor = get_pipeline_executor()
    
    try:
        job_id, states = await executor.execute_full_pipeline(
            bronze_only=pipeline_request.bronze_only,
            silver_only=pipeline_request.silver_only,
            force=pipeline_request.force,
            user_id=user_id
        )
        
        # Summarize results
        total = len(states)
        succeeded = sum(1 for s in states if s.status == PipelineStatus.SUCCESS)
        failed = sum(1 for s in states if s.status == PipelineStatus.FAILED)
        
        return {
            "job_id": job_id,
            "status": "success" if failed == 0 else "partial",
            "total_pipelines": total,
            "succeeded": succeeded,
            "failed": failed,
            "pipelines": [s.to_dict() for s in states]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{run_id}", response_model=PipelineStatusResponse)
@limiter.limit("60/minute")
async def get_pipeline_status(
    request: Request,
    run_id: str,
    api_key: str = Depends(verify_api_key)
):
    """
    Get status of a pipeline run.
    
    Args:
        run_id: Pipeline run ID
        api_key: API key for authentication
        
    Returns:
        Pipeline status details
    """
    executor = get_pipeline_executor()
    state = executor.get_execution_state(run_id)
    
    if state is None:
        raise HTTPException(status_code=404, detail=f"Run ID {run_id} not found")
    
    state_dict = state.to_dict()
    
    return PipelineStatusResponse(
        run_id=state_dict["run_id"],
        pipeline_name=state_dict["pipeline_name"],
        layer=PipelineLayer(state_dict["layer"]),
        status=PipelineStatus(state_dict["status"]),
        started_at=datetime.fromisoformat(state_dict["started_at"]) if state_dict["started_at"] else datetime.utcnow(),
        completed_at=datetime.fromisoformat(state_dict["completed_at"]) if state_dict["completed_at"] else None,
        duration_seconds=state_dict.get("duration_seconds"),
        message=state_dict.get("message", ""),
        error=state_dict.get("error"),
        stats=state_dict.get("stats")
    )


@router.get("/history")
@limiter.limit("60/minute")
async def get_pipeline_history(
    request: Request,
    limit: int = 50,
    api_key: str = Depends(verify_api_key)
):
    """
    Get recent pipeline execution history.
    
    Args:
        limit: Maximum number of entries to return
        api_key: API key for authentication
        
    Returns:
        List of recent pipeline executions
    """
    executor = get_pipeline_executor()
    history = executor.get_execution_history(limit=limit)
    
    return {
        "history": history,
        "count": len(history)
    }


@router.get("/list", response_model=PipelineListResponse)
@limiter.limit("60/minute")
async def list_pipelines(
    request: Request,
    layer: str = None,
    api_key: str = Depends(verify_api_key)
):
    """
    List all available pipelines.
    
    Args:
        layer: Optional layer filter (bronze/silver/gold)
        api_key: API key for authentication
        
    Returns:
        List of available pipelines
    """
    registry = get_registry()
    
    layer_filter = None
    if layer:
        try:
            layer_filter = PipelineLayer(layer)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid layer: {layer}")
    
    pipelines = registry.list_pipelines(layer=layer_filter)
    
    return PipelineListResponse(pipelines=pipelines)

