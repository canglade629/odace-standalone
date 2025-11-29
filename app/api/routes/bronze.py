"""Bronze layer API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.auth import verify_api_key
from app.core.models import PipelineRunRequest, PipelineRunResponse, PipelineLayer, PipelineStatus
from app.core.pipeline_executor import get_pipeline_executor
from app.core.job_manager import get_job_manager, JobStatus
from app.core.rate_limiter import limiter
from datetime import datetime
import uuid

router = APIRouter(prefix="/api/bronze", tags=["bronze"])


@router.post("/{pipeline_name}")
@limiter.limit("60/minute")
async def run_bronze_pipeline(
    request: Request,
    pipeline_name: str,
    force: bool = False,
    api_key: str = Depends(verify_api_key)
):
    """
    Run a specific bronze layer pipeline.
    
    Args:
        pipeline_name: Name of the bronze pipeline to run
        force: Force reprocessing of all files
        api_key: API key for authentication
        
    Returns:
        Pipeline run response with job ID and status
    """
    executor = get_pipeline_executor()
    job_manager = get_job_manager()
    
    try:
        # Create a job for this single pipeline execution
        job_name = f"bronze.{pipeline_name}"
        job = job_manager.create_job(job_name, total_tasks=1)
        job_id = job.job_id
        
        # Update job status to running
        job_manager.update_job_progress(job_id, status=JobStatus.RUNNING)
        
        # Execute pipeline
        state = await executor.execute_pipeline(
            PipelineLayer.BRONZE,
            pipeline_name,
            force=force,
            job_id=job_id
        )
        
        # Update job status based on result
        final_status = JobStatus.SUCCESS if state.status == PipelineStatus.SUCCESS else JobStatus.FAILED
        job_manager.update_job_progress(
            job_id,
            status=final_status,
            completed_tasks=1 if state.status == PipelineStatus.SUCCESS else 0,
            failed_tasks=1 if state.status == PipelineStatus.FAILED else 0,
            completed_at=datetime.utcnow()
        )
        
        return {
            "job_id": job_id,
            "run_id": state.run_id,
            "pipeline_name": pipeline_name,
            "layer": PipelineLayer.BRONZE.value,
            "status": state.status.value,
            "started_at": state.started_at.isoformat() if state.started_at else None,
            "message": f"Pipeline {pipeline_name} execution completed with status: {state.status.value}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

