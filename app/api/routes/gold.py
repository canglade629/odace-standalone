"""Gold layer API endpoints (placeholder)."""
from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.auth import verify_api_key
from app.core.models import PipelineRunResponse
from app.core.rate_limiter import limiter

router = APIRouter(prefix="/api/gold", tags=["gold"])


@router.post("/{pipeline_name}", response_model=PipelineRunResponse)
@limiter.limit("60/minute")
async def run_gold_pipeline(
    request: Request,
    pipeline_name: str,
    force: bool = False,
    api_key: str = Depends(verify_api_key)
):
    """
    Run a specific gold layer pipeline (placeholder).
    
    Args:
        pipeline_name: Name of the gold pipeline to run
        force: Force reprocessing
        api_key: API key for authentication
        
    Returns:
        Pipeline run response
    """
    raise HTTPException(
        status_code=501,
        detail="Gold layer pipelines not yet implemented. Add gold pipelines as needed."
    )

