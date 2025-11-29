"""Job tracking API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.auth import verify_api_key
from app.core.job_manager import get_job_manager
from app.core.rate_limiter import limiter
from typing import List, Dict, Any

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("")
@limiter.limit("60/minute")
async def list_jobs(
    request: Request,
    limit: int = 50,
    api_key: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    List recent jobs with progress.
    
    Args:
        limit: Maximum number of jobs to return
        api_key: API key for authentication
        
    Returns:
        List of jobs with progress information
    """
    job_manager = get_job_manager()
    
    try:
        jobs = job_manager.list_jobs(limit=limit)
        
        return {
            "jobs": jobs,
            "count": len(jobs)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}")
@limiter.limit("60/minute")
async def get_job(
    request: Request,
    job_id: str,
    api_key: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Get job details including all tasks.
    
    Args:
        job_id: Job ID
        api_key: API key for authentication
        
    Returns:
        Job details with task breakdown
    """
    job_manager = get_job_manager()
    
    try:
        job_data = job_manager.get_job(job_id, include_tasks=True)
        
        if job_data is None:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        return job_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

