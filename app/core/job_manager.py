"""Job and Task management with Firestore persistence."""
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
import logging
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


class TaskStatus(str, Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task:
    """Represents a single pipeline execution task."""
    
    def __init__(
        self,
        task_id: str,
        pipeline_name: str,
        layer: str,
        status: TaskStatus = TaskStatus.PENDING,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        duration_seconds: Optional[float] = None,
        message: str = "",
        error: Optional[str] = None,
        stats: Optional[Dict[str, Any]] = None
    ):
        self.task_id = task_id
        self.pipeline_name = pipeline_name
        self.layer = layer
        self.status = status
        self.started_at = started_at
        self.completed_at = completed_at
        self.duration_seconds = duration_seconds
        self.message = message
        self.error = error
        self.stats = stats
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for Firestore."""
        return {
            "task_id": self.task_id,
            "pipeline_name": self.pipeline_name,
            "layer": self.layer,
            "status": self.status.value if isinstance(self.status, TaskStatus) else self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
            "message": self.message,
            "error": self.error,
            "stats": self.stats
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Task':
        """Create task from dictionary."""
        return Task(
            task_id=data["task_id"],
            pipeline_name=data["pipeline_name"],
            layer=data["layer"],
            status=TaskStatus(data["status"]) if isinstance(data["status"], str) else data["status"],
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            duration_seconds=data.get("duration_seconds"),
            message=data.get("message", ""),
            error=data.get("error"),
            stats=data.get("stats")
        )


class Job:
    """Represents a job containing multiple pipeline tasks."""
    
    def __init__(
        self,
        job_id: str,
        job_name: str,
        status: JobStatus = JobStatus.PENDING,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        total_tasks: int = 0,
        completed_tasks: int = 0,
        failed_tasks: int = 0,
        progress_percent: float = 0.0,
        user_id: Optional[str] = None
    ):
        self.job_id = job_id
        self.job_name = job_name
        self.status = status
        self.started_at = started_at
        self.completed_at = completed_at
        self.total_tasks = total_tasks
        self.completed_tasks = completed_tasks
        self.failed_tasks = failed_tasks
        self.progress_percent = progress_percent
        self.user_id = user_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert job to dictionary for Firestore."""
        return {
            "job_id": self.job_id,
            "job_name": self.job_name,
            "status": self.status.value if isinstance(self.status, JobStatus) else self.status,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "progress_percent": self.progress_percent,
            "user_id": self.user_id
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Job':
        """Create job from dictionary."""
        return Job(
            job_id=data["job_id"],
            job_name=data["job_name"],
            status=JobStatus(data["status"]) if isinstance(data["status"], str) else data["status"],
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            total_tasks=data.get("total_tasks", 0),
            completed_tasks=data.get("completed_tasks", 0),
            failed_tasks=data.get("failed_tasks", 0),
            progress_percent=data.get("progress_percent", 0.0),
            user_id=data.get("user_id")
        )


class JobManager:
    """Manages jobs and tasks with Firestore persistence."""
    
    def __init__(self):
        """Initialize JobManager with Firestore client."""
        settings = get_settings()
        self.db = firestore.Client(project=settings.gcp_project_id)
        self.jobs_collection = "jobs"
    
    def create_job(self, job_name: str, total_tasks: int = 0, user_id: Optional[str] = None) -> Job:
        """
        Create a new job.
        
        Args:
            job_name: Name of the job
            total_tasks: Total number of tasks in this job
            user_id: ID of the user who triggered the job
            
        Returns:
            Created Job object
        """
        job_id = str(uuid.uuid4())
        job = Job(
            job_id=job_id,
            job_name=job_name,
            status=JobStatus.PENDING,
            started_at=datetime.utcnow(),
            total_tasks=total_tasks,
            completed_tasks=0,
            failed_tasks=0,
            progress_percent=0.0,
            user_id=user_id
        )
        
        # Save to Firestore
        self.db.collection(self.jobs_collection).document(job_id).set(job.to_dict())
        logger.info(f"Created job {job_id}: {job_name} (user: {user_id})")
        
        return job
    
    def update_job(self, job: Job) -> None:
        """
        Update an existing job in Firestore.
        
        Args:
            job: Job object to update
        """
        self.db.collection(self.jobs_collection).document(job.job_id).update(job.to_dict())
        logger.debug(f"Updated job {job.job_id}")
    
    def update_job_progress(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        total_tasks: Optional[int] = None,
        completed_tasks: Optional[int] = None,
        failed_tasks: Optional[int] = None,
        completed_at: Optional[datetime] = None
    ) -> None:
        """
        Update job progress.
        
        Args:
            job_id: Job ID
            status: New status (optional)
            total_tasks: Total number of tasks (optional)
            completed_tasks: Number of completed tasks (optional)
            failed_tasks: Number of failed tasks (optional)
            completed_at: Completion timestamp (optional)
        """
        job_ref = self.db.collection(self.jobs_collection).document(job_id)
        job_data = job_ref.get().to_dict()
        
        if job_data is None:
            logger.error(f"Job {job_id} not found")
            return
        
        updates = {}
        
        if status is not None:
            updates["status"] = status.value if isinstance(status, JobStatus) else status
        
        if total_tasks is not None:
            updates["total_tasks"] = total_tasks
        
        if completed_tasks is not None:
            updates["completed_tasks"] = completed_tasks
            # Calculate progress
            # Use updated total_tasks if provided, otherwise use existing
            total = total_tasks if total_tasks is not None else job_data.get("total_tasks", 0)
            if total > 0:
                updates["progress_percent"] = (completed_tasks / total) * 100
        
        if failed_tasks is not None:
            updates["failed_tasks"] = failed_tasks
        
        if completed_at is not None:
            updates["completed_at"] = completed_at
        
        if updates:
            job_ref.update(updates)
            logger.debug(f"Updated job {job_id} progress: {updates}")
    
    def add_task(self, job_id: str, task: Task) -> None:
        """
        Add a task to a job.
        
        Args:
            job_id: Job ID
            task: Task object to add
        """
        task_ref = (
            self.db.collection(self.jobs_collection)
            .document(job_id)
            .collection("tasks")
            .document(task.task_id)
        )
        task_ref.set(task.to_dict())
        logger.debug(f"Added task {task.task_id} to job {job_id}")
    
    def update_task(self, job_id: str, task: Task) -> None:
        """
        Update an existing task.
        
        Args:
            job_id: Job ID
            task: Task object to update
        """
        task_ref = (
            self.db.collection(self.jobs_collection)
            .document(job_id)
            .collection("tasks")
            .document(task.task_id)
        )
        task_ref.update(task.to_dict())
        logger.debug(f"Updated task {task.task_id} in job {job_id}")
    
    def get_job(self, job_id: str, include_tasks: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get a job by ID.
        
        Args:
            job_id: Job ID
            include_tasks: Whether to include tasks in the response
            
        Returns:
            Job dictionary with optional tasks list, or None if not found
        """
        job_ref = self.db.collection(self.jobs_collection).document(job_id)
        job_doc = job_ref.get()
        
        if not job_doc.exists:
            return None
        
        job_data = job_doc.to_dict()
        
        if include_tasks:
            # Fetch all tasks for this job
            tasks_ref = job_ref.collection("tasks")
            tasks = []
            for task_doc in tasks_ref.stream():
                tasks.append(task_doc.to_dict())
            
            # Sort tasks by started_at
            tasks.sort(key=lambda t: t.get("started_at") or datetime.min)
            job_data["tasks"] = tasks
        
        return job_data
    
    def list_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        List recent jobs.
        
        Args:
            limit: Maximum number of jobs to return
            
        Returns:
            List of job dictionaries
        """
        jobs_ref = (
            self.db.collection(self.jobs_collection)
            .order_by("started_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
        )
        
        jobs = []
        for job_doc in jobs_ref.stream():
            jobs.append(job_doc.to_dict())
        
        return jobs
    
    def get_tasks_for_job(self, job_id: str) -> List[Dict[str, Any]]:
        """
        Get all tasks for a specific job.
        
        Args:
            job_id: Job ID
            
        Returns:
            List of task dictionaries
        """
        tasks_ref = (
            self.db.collection(self.jobs_collection)
            .document(job_id)
            .collection("tasks")
            .order_by("started_at")
        )
        
        tasks = []
        for task_doc in tasks_ref.stream():
            tasks.append(task_doc.to_dict())
        
        return tasks


# Global job manager instance
_job_manager: Optional[JobManager] = None


def get_job_manager() -> JobManager:
    """Get or create global job manager instance."""
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager()
    return _job_manager

