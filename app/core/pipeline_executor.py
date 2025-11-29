"""Pipeline execution engine with DAG-based dependency resolution."""
import asyncio
from typing import List, Dict, Any, Set, Optional
from datetime import datetime
import uuid
import logging
from enum import Enum

from app.core.pipeline_registry import get_registry
from app.core.models import PipelineLayer, PipelineStatus
from app.core.job_manager import get_job_manager, Job, Task, JobStatus, TaskStatus

logger = logging.getLogger(__name__)


class PipelineExecutionState:
    """Track state of a pipeline execution."""
    
    def __init__(self, run_id: str, pipeline_name: str, layer: PipelineLayer):
        self.run_id = run_id
        self.pipeline_name = pipeline_name
        self.layer = layer
        self.status = PipelineStatus.PENDING
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        duration = None
        if self.started_at and self.completed_at:
            duration = (self.completed_at - self.started_at).total_seconds()
        
        return {
            "run_id": self.run_id,
            "pipeline_name": self.pipeline_name,
            "layer": self.layer.value,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": duration,
            "message": self.result.get("message", "") if self.result else "",
            "error": self.error,
            "stats": self.result if self.result else None
        }


class PipelineExecutor:
    """Execute pipelines with dependency resolution."""
    
    def __init__(self):
        self.registry = get_registry()
        self.execution_history: Dict[str, PipelineExecutionState] = {}
        self.job_manager = get_job_manager()
        self.current_job_id: Optional[str] = None
    
    def _resolve_dependencies(
        self,
        layer: PipelineLayer,
        name: str,
        visited: Optional[Set[str]] = None
    ) -> List[tuple]:
        """
        Resolve pipeline dependencies using topological sort.
        
        Args:
            layer: Pipeline layer
            name: Pipeline name
            visited: Set of already visited pipelines (for cycle detection)
            
        Returns:
            List of (layer, name) tuples in execution order
        """
        if visited is None:
            visited = set()
        
        full_name = f"{layer.value}.{name}"
        
        # Check for circular dependencies
        if full_name in visited:
            raise ValueError(f"Circular dependency detected: {full_name}")
        
        visited.add(full_name)
        
        # Get dependencies for this pipeline
        dependencies = self.registry.get_dependencies(layer, name)
        
        # Resolve each dependency recursively
        execution_order = []
        for dep in dependencies:
            if "." in dep:
                dep_layer_str, dep_name = dep.split(".", 1)
                dep_layer = PipelineLayer(dep_layer_str)
                
                # Recursively resolve sub-dependencies
                sub_deps = self._resolve_dependencies(dep_layer, dep_name, visited.copy())
                execution_order.extend(sub_deps)
        
        # Add this pipeline after its dependencies
        execution_order.append((layer, name))
        
        # Remove duplicates while preserving order
        seen = set()
        unique_order = []
        for item in execution_order:
            if item not in seen:
                seen.add(item)
                unique_order.append(item)
        
        return unique_order
    
    async def execute_pipeline(
        self,
        layer: PipelineLayer,
        name: str,
        force: bool = False,
        run_id: Optional[str] = None,
        job_id: Optional[str] = None
    ) -> PipelineExecutionState:
        """
        Execute a single pipeline.
        
        Args:
            layer: Pipeline layer
            name: Pipeline name
            force: Force reprocessing
            run_id: Optional run ID (generated if not provided)
            job_id: Optional job ID to associate this execution with
            
        Returns:
            Execution state
        """
        if run_id is None:
            run_id = str(uuid.uuid4())
        
        state = PipelineExecutionState(run_id, name, layer)
        self.execution_history[run_id] = state
        
        logger.info(f"Executing pipeline: {layer.value}.{name} (run_id={run_id})")
        
        # Create task in job if job_id provided
        if job_id:
            task = Task(
                task_id=run_id,
                pipeline_name=name,
                layer=layer.value,
                status=TaskStatus.PENDING,
                started_at=datetime.utcnow()
            )
            self.job_manager.add_task(job_id, task)
        
        # Get pipeline class
        pipeline_class = self.registry.get(layer, name)
        if pipeline_class is None:
            state.status = PipelineStatus.FAILED
            state.error = f"Pipeline {layer.value}.{name} not found"
            logger.error(state.error)
            
            # Update task if part of job
            if job_id:
                task.status = TaskStatus.FAILED
                task.error = state.error
                task.completed_at = datetime.utcnow()
                self.job_manager.update_task(job_id, task)
            
            return state
        
        # Execute the pipeline
        state.status = PipelineStatus.RUNNING
        state.started_at = datetime.utcnow()
        
        # Update task status to running
        if job_id:
            task.status = TaskStatus.RUNNING
            self.job_manager.update_task(job_id, task)
        
        try:
            # Instantiate and run pipeline
            pipeline = pipeline_class()
            result = await asyncio.to_thread(pipeline.run, force=force)
            
            # Map result status to pipeline/task status
            result_status = result.get("status", "success")
            if result_status == "failed":
                state.status = PipelineStatus.FAILED
                task_status = TaskStatus.FAILED
            elif result_status == "partial":
                # Partial means some errors occurred
                state.status = PipelineStatus.FAILED
                task_status = TaskStatus.FAILED
            else:
                state.status = PipelineStatus.SUCCESS
                task_status = TaskStatus.SUCCESS
            
            state.result = result
            state.completed_at = datetime.utcnow()
            
            # Update task with appropriate status
            if job_id:
                task.status = task_status
                task.completed_at = state.completed_at
                task.duration_seconds = (state.completed_at - state.started_at).total_seconds()
                task.message = result.get("message", "")
                task.error = result.get("error") if result_status == "failed" else None
                task.stats = result
                self.job_manager.update_task(job_id, task)
            
            logger.info(f"Pipeline {layer.value}.{name} completed with status: {result_status}")
            
        except Exception as e:
            state.status = PipelineStatus.FAILED
            state.error = str(e)
            state.completed_at = datetime.utcnow()
            
            # Update task on failure
            if job_id:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                task.completed_at = state.completed_at
                task.duration_seconds = (state.completed_at - state.started_at).total_seconds()
                self.job_manager.update_task(job_id, task)
            
            logger.error(f"Pipeline {layer.value}.{name} failed: {e}", exc_info=True)
        
        return state
    
    async def execute_with_dependencies(
        self,
        layer: PipelineLayer,
        name: str,
        force: bool = False,
        job_id: Optional[str] = None
    ) -> List[PipelineExecutionState]:
        """
        Execute a pipeline and all its dependencies.
        
        Args:
            layer: Pipeline layer
            name: Pipeline name
            force: Force reprocessing
            job_id: Optional job ID to associate executions with
            
        Returns:
            List of execution states for all pipelines
        """
        logger.info(f"Resolving dependencies for {layer.value}.{name}")
        
        # Resolve execution order
        try:
            execution_order = self._resolve_dependencies(layer, name)
        except ValueError as e:
            logger.error(f"Dependency resolution failed: {e}")
            raise
        
        logger.info(f"Execution order: {execution_order}")
        
        # Execute each pipeline in order
        results = []
        for exec_layer, exec_name in execution_order:
            state = await self.execute_pipeline(exec_layer, exec_name, force=force, job_id=job_id)
            results.append(state)
            
            # Stop if a pipeline failed
            if state.status == PipelineStatus.FAILED:
                logger.error(f"Stopping execution due to failure in {exec_layer.value}.{exec_name}")
                break
        
        return results
    
    async def execute_full_pipeline(
        self,
        bronze_only: bool = False,
        silver_only: bool = False,
        force: bool = False,
        user_id: Optional[str] = None
    ) -> tuple[str, List[PipelineExecutionState]]:
        """
        Execute the full data pipeline.
        
        Args:
            bronze_only: Run only bronze layer
            silver_only: Run only silver layer
            force: Force reprocessing
            user_id: ID of the user triggering the pipeline
            
        Returns:
            Tuple of (job_id, list of execution states)
        """
        # Determine job name
        if bronze_only:
            job_name = "Full Pipeline - Bronze Only"
        elif silver_only:
            job_name = "Full Pipeline - Silver Only"
        else:
            job_name = "Full Pipeline - Bronze → Silver"
        
        # Count total tasks
        total_tasks = 0
        if not silver_only:
            bronze_pipelines = self.registry.list_pipelines(PipelineLayer.BRONZE)
            total_tasks += len(bronze_pipelines)
        
        if not bronze_only:
            silver_pipelines = self.registry.list_pipelines(PipelineLayer.SILVER)
            # Each silver pipeline may have dependencies, but we count unique pipelines
            total_tasks += len(silver_pipelines)
        
        # Create job
        job = self.job_manager.create_job(job_name, total_tasks, user_id=user_id)
        job_id = job.job_id
        self.current_job_id = job_id
        
        # Update job status to running
        self.job_manager.update_job_progress(job_id, status=JobStatus.RUNNING)
        
        results = []
        completed = 0
        failed = 0
        
        try:
            # Run bronze layer
            if not silver_only:
                logger.info("Running all bronze pipelines")
                bronze_pipelines = self.registry.list_pipelines(PipelineLayer.BRONZE)
                
                for pipeline_info in bronze_pipelines:
                    state = await self.execute_pipeline(
                        PipelineLayer.BRONZE,
                        pipeline_info.name,
                        force=force,
                        job_id=job_id
                    )
                    results.append(state)
                    
                    if state.status == PipelineStatus.SUCCESS:
                        completed += 1
                    elif state.status == PipelineStatus.FAILED:
                        failed += 1
                        # Fail-fast: Stop execution on first failure
                        logger.error(f"Task {pipeline_info.name} failed, stopping remaining pipelines")
                    
                    # Update job progress
                    self.job_manager.update_job_progress(
                        job_id,
                        completed_tasks=completed,
                        failed_tasks=failed
                    )
                    
                    # Break on first failure (fail-fast)
                    if state.status == PipelineStatus.FAILED:
                        break
            
            # Run silver layer (only if no failures in bronze and not bronze_only)
            if not bronze_only and failed == 0:
                logger.info("Running all silver pipelines")
                silver_pipelines = self.registry.list_pipelines(PipelineLayer.SILVER)
                
                for pipeline_info in silver_pipelines:
                    # In full pipeline mode, bronze is already run, so don't re-run dependencies
                    # Just run the silver pipeline directly
                    state = await self.execute_pipeline(
                        PipelineLayer.SILVER,
                        pipeline_info.name,
                        force=force,
                        job_id=job_id
                    )
                    results.append(state)
                    
                    if state.status == PipelineStatus.SUCCESS:
                        completed += 1
                    elif state.status == PipelineStatus.FAILED:
                        failed += 1
                        # Fail-fast: Stop execution on first failure
                        logger.error(f"Task {pipeline_info.name} failed, stopping remaining pipelines")
                    
                    # Update job progress
                    self.job_manager.update_job_progress(
                        job_id,
                        completed_tasks=completed,
                        failed_tasks=failed
                    )
                    
                    # Break on first failure (fail-fast)
                    if state.status == PipelineStatus.FAILED:
                        break
            
            # Determine final job status
            # If any task failed, the entire job is considered failed
            if failed > 0:
                final_status = JobStatus.FAILED
            else:
                final_status = JobStatus.SUCCESS
            
            # Mark job as completed
            self.job_manager.update_job_progress(
                job_id,
                status=final_status,
                completed_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Full pipeline execution failed: {e}", exc_info=True)
            self.job_manager.update_job_progress(
                job_id,
                status=JobStatus.FAILED,
                completed_at=datetime.utcnow()
            )
            raise
        finally:
            self.current_job_id = None
        
        return job_id, results
    
    def get_execution_state(self, run_id: str) -> Optional[PipelineExecutionState]:
        """
        Get execution state by run ID.
        
        Args:
            run_id: Run ID
            
        Returns:
            Execution state or None
        """
        return self.execution_history.get(run_id)
    
    def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent execution history.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of execution states as dictionaries
        """
        # Sort by started_at descending
        sorted_executions = sorted(
            self.execution_history.values(),
            key=lambda x: x.started_at or datetime.min,
            reverse=True
        )
        
        return [state.to_dict() for state in sorted_executions[:limit]]


# Global executor instance
_executor: Optional[PipelineExecutor] = None


def get_pipeline_executor() -> PipelineExecutor:
    """Get or create global pipeline executor instance."""
    global _executor
    if _executor is None:
        _executor = PipelineExecutor()
    return _executor

