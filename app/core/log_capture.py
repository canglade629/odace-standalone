"""Log capture handler for storing pipeline logs in Firestore."""
import logging
import threading
import time
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from queue import Queue, Empty
from google.cloud import firestore

from app.core.config import get_settings


class FirestoreLogHandler(logging.Handler):
    """Custom logging handler that writes logs to Firestore with batching."""
    
    def __init__(
        self,
        job_id: str,
        task_id: Optional[str] = None,
        batch_size: int = 10,
        flush_interval: float = 2.0
    ):
        """
        Initialize Firestore log handler.
        
        Args:
            job_id: Job ID to associate logs with
            task_id: Optional task ID for task-specific logs
            batch_size: Number of logs to batch before writing
            flush_interval: Maximum time (seconds) to wait before flushing
        """
        super().__init__()
        settings = get_settings()
        self.db = firestore.Client(project=settings.gcp_project_id)
        self.job_id = job_id
        self.task_id = task_id
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        # Queue for batching logs
        self.log_queue: Queue = Queue()
        self.is_running = True
        
        # Background thread for flushing logs
        self.flush_thread = threading.Thread(target=self._flush_worker, daemon=True)
        self.flush_thread.start()
    
    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record.
        
        Args:
            record: Log record to emit
        """
        try:
            # Format the log message
            message = self.format(record)
            
            # Create log entry
            log_entry = {
                "timestamp": datetime.utcnow(),
                "level": record.levelname,
                "message": message,
                "logger_name": record.name,
                "job_id": self.job_id,
            }
            
            # Add task_id if available
            if self.task_id:
                log_entry["task_id"] = self.task_id
            
            # Add to queue
            self.log_queue.put(log_entry)
            
        except Exception:
            self.handleError(record)
    
    def _flush_worker(self) -> None:
        """Background worker that flushes logs to Firestore."""
        batch: List[Dict[str, Any]] = []
        last_flush = time.time()
        
        while self.is_running:
            try:
                # Try to get log with timeout
                try:
                    log_entry = self.log_queue.get(timeout=0.5)
                    batch.append(log_entry)
                except Empty:
                    pass
                
                # Flush if batch is full or time interval exceeded
                current_time = time.time()
                should_flush = (
                    len(batch) >= self.batch_size or
                    (batch and current_time - last_flush >= self.flush_interval)
                )
                
                if should_flush:
                    self._write_batch(batch)
                    batch = []
                    last_flush = current_time
                    
            except Exception as e:
                # Log error but don't crash the thread
                print(f"Error in log flush worker: {e}")
        
        # Final flush on shutdown
        if batch:
            self._write_batch(batch)
    
    def _write_batch(self, batch: List[Dict[str, Any]]) -> None:
        """
        Write a batch of logs to Firestore.
        
        Args:
            batch: List of log entries to write
        """
        if not batch:
            return
        
        try:
            # Use batch write for efficiency
            db_batch = self.db.batch()
            logs_collection = (
                self.db.collection("jobs")
                .document(self.job_id)
                .collection("logs")
            )
            
            for log_entry in batch:
                doc_ref = logs_collection.document()
                db_batch.set(doc_ref, log_entry)
            
            db_batch.commit()
            
        except Exception as e:
            print(f"Failed to write logs to Firestore: {e}")
    
    def flush(self) -> None:
        """Flush any buffered logs."""
        # Give worker thread time to process remaining logs
        time.sleep(self.flush_interval + 0.5)
    
    def close(self) -> None:
        """Close the handler and stop background thread."""
        self.is_running = False
        
        # Wait for worker thread to finish
        if self.flush_thread.is_alive():
            self.flush_thread.join(timeout=5.0)
        
        super().close()


class LogCaptureContext:
    """Context manager for capturing logs during pipeline execution."""
    
    def __init__(
        self,
        job_id: str,
        task_id: Optional[str] = None,
        logger_name: str = "app"
    ):
        """
        Initialize log capture context.
        
        Args:
            job_id: Job ID to associate logs with
            task_id: Optional task ID for task-specific logs
            logger_name: Name of logger to capture (default: "app")
        """
        self.job_id = job_id
        self.task_id = task_id
        self.logger_name = logger_name
        self.handler: Optional[FirestoreLogHandler] = None
        self.logger: Optional[logging.Logger] = None
    
    def __enter__(self) -> 'LogCaptureContext':
        """Start capturing logs."""
        # Create handler
        self.handler = FirestoreLogHandler(self.job_id, self.task_id)
        
        # Set formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.handler.setFormatter(formatter)
        
        # Add to logger
        self.logger = logging.getLogger(self.logger_name)
        self.logger.addHandler(self.handler)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop capturing logs."""
        if self.handler and self.logger:
            # Remove handler
            self.logger.removeHandler(self.handler)
            
            # Close handler (flushes remaining logs)
            self.handler.close()
        
        return False


def cleanup_old_logs(days: int = 30) -> int:
    """
    Clean up logs older than specified days.
    
    Args:
        days: Number of days to keep logs
        
    Returns:
        Number of log documents deleted
    """
    settings = get_settings()
    db = firestore.Client(project=settings.gcp_project_id)
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    deleted_count = 0
    
    try:
        # Iterate through all jobs
        jobs_ref = db.collection("jobs")
        
        for job_doc in jobs_ref.stream():
            logs_ref = job_doc.reference.collection("logs")
            
            # Query old logs
            old_logs_query = logs_ref.where("timestamp", "<", cutoff_date).limit(500)
            
            # Delete in batches
            batch = db.batch()
            batch_count = 0
            
            for log_doc in old_logs_query.stream():
                batch.delete(log_doc.reference)
                batch_count += 1
                deleted_count += 1
                
                # Commit batch every 500 deletes
                if batch_count >= 500:
                    batch.commit()
                    batch = db.batch()
                    batch_count = 0
            
            # Commit remaining
            if batch_count > 0:
                batch.commit()
        
        return deleted_count
        
    except Exception as e:
        print(f"Error cleaning up old logs: {e}")
        return deleted_count

