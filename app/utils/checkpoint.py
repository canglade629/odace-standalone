"""Checkpoint system for tracking processed files."""
import pandas as pd
from datetime import datetime
from typing import List, Optional, Set
from app.utils.delta_ops import DeltaOperations
from app.core.config import get_settings
import logging

logger = logging.getLogger(__name__)


class CheckpointManager:
    """Manage checkpoints for idempotent file processing."""
    
    def __init__(self):
        """Initialize checkpoint manager."""
        self.settings = get_settings()
        self.checkpoint_path = self.settings.get_checkpoint_path()
        self.delta_ops = DeltaOperations()
        self._ensure_checkpoint_table()
    
    def _ensure_checkpoint_table(self):
        """Ensure checkpoint table exists."""
        if not self.delta_ops.table_exists(self.checkpoint_path):
            logger.info("Creating checkpoint table")
            # Create checkpoint table with initial dummy data to establish schema
            df = pd.DataFrame([{
                'pipeline_name': '_init',
                'file_path': '_init',
                'file_hash': '_init',
                'processed_at': pd.Timestamp.now(),
                'status': '_init',
                'rows_processed': 0
            }])
            self.delta_ops.write_delta(df, self.checkpoint_path, mode="overwrite")
    
    def get_processed_files(self, pipeline_name: str) -> Set[str]:
        """
        Get set of files already processed by a pipeline.
        
        Args:
            pipeline_name: Name of the pipeline
            
        Returns:
            Set of file paths that have been processed
        """
        try:
            df = self.delta_ops.read_delta(self.checkpoint_path)
            # Filter by pipeline and successful status
            mask = (df['pipeline_name'] == pipeline_name) & (df['status'] == 'success')
            processed = set(df[mask]['file_path'].tolist())
            logger.info(f"Found {len(processed)} processed files for {pipeline_name}")
            return processed
        except Exception as e:
            logger.warning(f"Could not read checkpoints: {e}")
            return set()
    
    def mark_file_processed(
        self,
        pipeline_name: str,
        file_path: str,
        file_hash: str,
        rows_processed: int = 0,
        status: str = "success"
    ):
        """
        Mark a file as processed.
        
        Args:
            pipeline_name: Name of the pipeline
            file_path: Full path to the file
            file_hash: Hash of the file (for change detection)
            rows_processed: Number of rows processed
            status: Processing status (success/failed)
        """
        checkpoint_entry = pd.DataFrame([{
            'pipeline_name': pipeline_name,
            'file_path': file_path,
            'file_hash': file_hash,
            'processed_at': datetime.utcnow(),
            'status': status,
            'rows_processed': rows_processed
        }])
        
        self.delta_ops.write_delta(
            checkpoint_entry,
            self.checkpoint_path,
            mode="append"
        )
        logger.info(f"Marked {file_path} as {status} for {pipeline_name}")
    
    def get_new_files(self, pipeline_name: str, all_files: List[str]) -> List[str]:
        """
        Filter list of files to only those not yet processed.
        
        Args:
            pipeline_name: Name of the pipeline
            all_files: List of all available files
            
        Returns:
            List of files that haven't been processed yet
        """
        processed = self.get_processed_files(pipeline_name)
        new_files = [f for f in all_files if f not in processed]
        logger.info(f"Found {len(new_files)} new files out of {len(all_files)} total")
        return new_files
    
    def clear_checkpoints(self, pipeline_name: str):
        """
        Clear checkpoints for a pipeline (for force refresh).
        
        Args:
            pipeline_name: Name of the pipeline
        """
        try:
            df = self.delta_ops.read_delta(self.checkpoint_path)
            # Keep only checkpoints for other pipelines
            df_filtered = df[df['pipeline_name'] != pipeline_name]
            self.delta_ops.write_delta(
                df_filtered,
                self.checkpoint_path,
                mode="overwrite"
            )
            logger.info(f"Cleared checkpoints for {pipeline_name}")
        except Exception as e:
            logger.error(f"Failed to clear checkpoints: {e}")


# Global instance
_checkpoint_manager: Optional[CheckpointManager] = None


def get_checkpoint_manager() -> CheckpointManager:
    """Get or create global checkpoint manager instance."""
    global _checkpoint_manager
    if _checkpoint_manager is None:
        _checkpoint_manager = CheckpointManager()
    return _checkpoint_manager

