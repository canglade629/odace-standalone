"""Silver layer API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.auth import verify_api_key
from app.core.models import PipelineRunResponse, PipelineLayer, PipelineStatus
from app.core.pipeline_executor import get_pipeline_executor
from app.core.job_manager import get_job_manager, JobStatus
from app.core.rate_limiter import limiter
from datetime import datetime
import uuid

router = APIRouter(prefix="/api/silver", tags=["silver"])


@router.post("/{pipeline_name}")
@limiter.limit("60/minute")
async def run_silver_pipeline(
    request: Request,
    pipeline_name: str,
    force: bool = False,
    api_key: str = Depends(verify_api_key)
):
    """
    Run a specific silver layer pipeline with dependencies.
    
    Args:
        pipeline_name: Name of the silver pipeline to run
        force: Force reprocessing
        api_key: API key for authentication
        
    Returns:
        Pipeline run response with job ID and status
    """
    executor = get_pipeline_executor()
    job_manager = get_job_manager()
    
    try:
        # Create a job for this pipeline execution (including dependencies)
        job_name = f"silver.{pipeline_name}"
        # We don't know exact count yet, but will update as we go
        job = job_manager.create_job(job_name, total_tasks=1)
        job_id = job.job_id
        
        # Update job status to running
        job_manager.update_job_progress(job_id, status=JobStatus.RUNNING)
        
        # Execute with dependencies
        states = await executor.execute_with_dependencies(
            PipelineLayer.SILVER,
            pipeline_name,
            force=force,
            job_id=job_id
        )
        
        # Update total tasks count now that we know
        job_data = job_manager.get_job(job_id)
        if job_data:
            # Count successful and failed
            succeeded = sum(1 for s in states if s.status == PipelineStatus.SUCCESS)
            failed = sum(1 for s in states if s.status == PipelineStatus.FAILED)
            total = len(states)
            
            # Determine final status - if any task failed, job is failed
            if failed > 0:
                final_status = JobStatus.FAILED
            else:
                final_status = JobStatus.SUCCESS
            
            # Update job with final counts (including total_tasks)
            job_manager.update_job_progress(
                job_id,
                status=final_status,
                total_tasks=total,
                completed_tasks=succeeded,
                failed_tasks=failed,
                completed_at=datetime.utcnow()
            )
        
        # Return status of the main pipeline (last one)
        if states:
            main_state = states[-1]
            return {
                "job_id": job_id,
                "run_id": main_state.run_id,
                "pipeline_name": pipeline_name,
                "layer": PipelineLayer.SILVER.value,
                "status": main_state.status.value,
                "started_at": main_state.started_at.isoformat() if main_state.started_at else None,
                "message": f"Pipeline {pipeline_name} and dependencies completed"
            }
        else:
            raise HTTPException(status_code=500, detail="No pipelines executed")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

