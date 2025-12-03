"""Job tracking API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.auth import verify_api_key
from app.core.job_manager import get_job_manager
from app.core.pipeline_executor import get_pipeline_executor
from app.core.rate_limiter import limiter
from app.core.config import get_settings
from typing import List, Dict, Any
from google.cloud import firestore

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


@router.get("/{job_id}/logs")
@limiter.limit("60/minute")
async def get_job_logs(
    request: Request,
    job_id: str,
    task_id: str = None,
    limit: int = 1000,
    offset: int = 0,
    api_key: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Get logs for a specific job.
    
    Args:
        job_id: Job ID
        task_id: Optional task ID to filter logs
        limit: Maximum number of logs to return (default: 1000)
        offset: Number of logs to skip (default: 0)
        api_key: API key for authentication
        
    Returns:
        Logs for the job with metadata
    """
    settings = get_settings()
    db = firestore.Client(project=settings.gcp_project_id)
    
    try:
        # Verify job exists
        job_ref = db.collection("jobs").document(job_id)
        job_doc = job_ref.get()
        
        if not job_doc.exists:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        
        # Build query for logs
        logs_ref = job_ref.collection("logs")
        query = logs_ref.order_by("timestamp")
        
        # Filter by task_id if provided
        if task_id:
            query = query.where("task_id", "==", task_id)
        
        # Apply pagination
        if offset > 0:
            query = query.offset(offset)
        
        query = query.limit(limit)
        
        # Fetch logs
        logs = []
        for log_doc in query.stream():
            log_data = log_doc.to_dict()
            # Convert timestamp to ISO format for JSON serialization
            if log_data.get("timestamp"):
                log_data["timestamp"] = log_data["timestamp"].isoformat()
            logs.append(log_data)
        
        # Get total count (approximately, without scanning all documents)
        # For performance, we'll just return the count of fetched logs
        total_count = len(logs)
        
        return {
            "job_id": job_id,
            "logs": logs,
            "count": total_count,
            "limit": limit,
            "offset": offset
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/logs/stream")
@limiter.limit("60/minute")
async def get_all_logs_stream(
    request: Request,
    limit: int = 500,
    api_key: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Get recent logs from all jobs in chronological order.
    
    Args:
        limit: Maximum number of logs to return (default: 500)
        api_key: API key for authentication
        
    Returns:
        Combined logs from all recent jobs
    """
    settings = get_settings()
    db = firestore.Client(project=settings.gcp_project_id)
    
    try:
        # Get recent jobs (last 10)
        jobs_ref = db.collection("jobs").order_by("started_at", direction=firestore.Query.DESCENDING).limit(10)
        
        all_logs = []
        
        # Fetch logs from each job
        for job_doc in jobs_ref.stream():
            job_id = job_doc.id
            logs_ref = db.collection("jobs").document(job_id).collection("logs")
            
            # Get logs from this job
            for log_doc in logs_ref.order_by("timestamp").stream():
                log_data = log_doc.to_dict()
                # Convert timestamp to ISO format
                if log_data.get("timestamp"):
                    log_data["timestamp"] = log_data["timestamp"].isoformat()
                    log_data["_timestamp_obj"] = log_doc.to_dict().get("timestamp")  # Keep for sorting
                all_logs.append(log_data)
        
        # Sort all logs by timestamp
        all_logs.sort(key=lambda x: x.get("_timestamp_obj") or "", reverse=False)
        
        # Remove the helper timestamp object and limit results
        for log in all_logs:
            log.pop("_timestamp_obj", None)
        
        all_logs = all_logs[-limit:]  # Keep most recent N logs
        
        return {
            "logs": all_logs,
            "count": len(all_logs)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{job_id}/cancel")
@limiter.limit("60/minute")
async def cancel_job(
    request: Request,
    job_id: str,
    api_key: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Cancel a running job.
    
    Args:
        job_id: Job ID to cancel
        api_key: API key for authentication
        
    Returns:
        Success message
    """
    executor = get_pipeline_executor()
    
    try:
        success = executor.cancel_job(job_id)
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"Could not cancel job {job_id}. Job may not exist or is not running."
            )
        
        return {
            "message": f"Job {job_id} has been cancelled",
            "job_id": job_id,
            "status": "cancelled"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

