"""Base pipeline classes for Bronze, Silver, and Gold layers."""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import pandas as pd
from datetime import datetime
import hashlib
import logging

from app.core.config import get_settings
from app.utils.gcs_ops import get_gcs_operations
from app.utils.delta_ops import DeltaOperations
from app.utils.checkpoint import get_checkpoint_manager
from app.utils.sql_executor import get_sql_executor

logger = logging.getLogger(__name__)


class BasePipeline(ABC):
    """Base class for all pipelines."""
    
    def __init__(self):
        """Initialize pipeline."""
        self.settings = get_settings()
        self.gcs = get_gcs_operations()
        self.delta_ops = DeltaOperations()
        self.checkpoint_mgr = get_checkpoint_manager()
        self.stats = {
            "files_processed": 0,
            "rows_processed": 0,
            "errors": []
        }
    
    @abstractmethod
    def get_name(self) -> str:
        """Get pipeline name."""
        pass
    
    @abstractmethod
    def run(self, force: bool = False) -> Dict[str, Any]:
        """
        Run the pipeline.
        
        Args:
            force: Force reprocessing even if checkpoints exist
            
        Returns:
            Dictionary with execution statistics
        """
        pass
    
    def _compute_file_hash(self, file_path: str) -> str:
        """
        Compute hash of a file for change detection.
        
        Args:
            file_path: GCS path to file
            
        Returns:
            MD5 hash of file contents
        """
        try:
            content = self.gcs.download_file(file_path)
            return hashlib.md5(content).hexdigest()
        except Exception as e:
            logger.warning(f"Could not compute hash for {file_path}: {e}")
            return ""


class BaseBronzePipeline(BasePipeline):
    """Base class for Bronze layer pipelines (ingestion)."""
    
    @abstractmethod
    def get_source_path(self) -> str:
        """Get GCS path to source files."""
        pass
    
    @abstractmethod
    def get_target_table(self) -> str:
        """Get target Delta table name."""
        pass
    
    @abstractmethod
    def read_source_file(self, file_path: str) -> pd.DataFrame:
        """
        Read a source file into a DataFrame.
        
        Args:
            file_path: GCS path to source file
            
        Returns:
            pandas DataFrame
        """
        pass
    
    def get_write_mode(self) -> str:
        """
        Get write mode for Delta table.
        
        Override this method to change from default 'append' to 'overwrite'.
        
        Returns:
            Write mode: 'append' or 'overwrite'
        """
        return "append"  # Process all files like Databricks Auto Loader
    
    def transform(self, df: pd.DataFrame, file_path: str) -> pd.DataFrame:
        """
        Transform the DataFrame (optional override).
        
        Default behavior: add ingestion_timestamp column
        
        Args:
            df: Input DataFrame
            file_path: Source file path (for extracting metadata)
            
        Returns:
            Transformed DataFrame
        """
        df['ingestion_timestamp'] = datetime.utcnow()
        return df
    
    def get_new_files(self, force: bool = False) -> List[str]:
        """
        Get list of files to process.
        
        Args:
            force: If True, return all files ignoring checkpoints
            
        Returns:
            List of file paths to process
        """
        source_path = self.get_source_path()
        # Extract prefix from gs://bucket/prefix
        prefix = source_path.replace(f"gs://{self.settings.gcs_bucket}/", "")
        
        all_files = self.gcs.list_files(prefix)
        
        # Process all files matching Databricks Auto Loader behavior
        # (Changed from "latest file only" to match Databricks streaming behavior)
        if force:
            logger.info(f"Force mode: processing all {len(all_files)} file(s)")
            return all_files
        
        return self.checkpoint_mgr.get_new_files(self.get_name(), all_files)
    
    def run(self, force: bool = False) -> Dict[str, Any]:
        """
        Run the bronze pipeline.
        
        Args:
            force: Force reprocessing of all files
            
        Returns:
            Execution statistics
        """
        logger.info(f"Running bronze pipeline: {self.get_name()}")
        
        if force:
            logger.info("Force mode enabled - clearing checkpoints")
            self.checkpoint_mgr.clear_checkpoints(self.get_name())
        
        # Get files to process
        files_to_process = self.get_new_files(force)
        
        if not files_to_process:
            logger.info("No new files to process")
            return {
                "status": "success",
                "files_processed": 0,
                "rows_processed": 0,
                "message": "No new files to process"
            }
        
        logger.info(f"Found {len(files_to_process)} files to process")
        
        # Process each file
        target_path = self.settings.get_bronze_path(self.get_target_table())
        
        # In force mode, overwrite on first file for idempotency, then append rest
        is_first_file = True
        
        for file_path in files_to_process:
            try:
                logger.info(f"Processing {file_path}")
                
                # Read source file
                df = self.read_source_file(file_path)
                
                # Transform
                df = self.transform(df, file_path)
                
                # Determine write mode for idempotency:
                # - Force mode: overwrite first file (clears old data), append rest
                # - Normal mode: use configured mode (default append)
                if force and is_first_file:
                    write_mode = "overwrite"
                    is_first_file = False
                else:
                    write_mode = self.get_write_mode()
                
                self.delta_ops.write_delta(
                    df,
                    target_path,
                    mode=write_mode
                )
                
                # Update checkpoint
                file_hash = self._compute_file_hash(file_path)
                self.checkpoint_mgr.mark_file_processed(
                    self.get_name(),
                    file_path,
                    file_hash,
                    rows_processed=len(df),
                    status="success"
                )
                
                self.stats["files_processed"] += 1
                self.stats["rows_processed"] += len(df)
                
                logger.info(f"Successfully processed {file_path}: {len(df)} rows")
                
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}", exc_info=True)
                self.stats["errors"].append({
                    "file": file_path,
                    "error": str(e)
                })
                # Mark as failed in checkpoint
                self.checkpoint_mgr.mark_file_processed(
                    self.get_name(),
                    file_path,
                    "",
                    status="failed"
                )
        
        # Determine status and message
        if self.stats["errors"]:
            status = "partial"
            message = f"Processed {self.stats['files_processed']} files with {len(self.stats['errors'])} errors"
        else:
            status = "success"
            if self.stats["files_processed"] == 0:
                message = "No new files to process"
            else:
                message = f"Successfully processed {self.stats['files_processed']} file(s), {self.stats['rows_processed']} rows"
        
        return {
            "status": status,
            "files_processed": self.stats["files_processed"],
            "rows_processed": self.stats["rows_processed"],
            "errors": self.stats["errors"],
            "message": message
        }


class BaseSilverPipeline(BasePipeline):
    """Base class for Silver layer pipelines (transformation)."""
    
    @abstractmethod
    def get_source_tables(self) -> List[str]:
        """
        Get list of source table names (bronze tables).
        
        Returns:
            List of table names
        """
        pass
    
    @abstractmethod
    def get_target_table(self) -> str:
        """Get target Delta table name."""
        pass
    
    @abstractmethod
    def transform(self, source_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Transform source data into target format.
        
        Args:
            source_data: Dictionary mapping table names to DataFrames
            
        Returns:
            Transformed DataFrame
        """
        pass
    
    def run(self, force: bool = False) -> Dict[str, Any]:
        """
        Run the silver pipeline.
        
        Args:
            force: Force reprocessing
            
        Returns:
            Execution statistics
        """
        logger.info(f"Running silver pipeline: {self.get_name()}")
        
        try:
            # Load source tables
            source_data = {}
            for table_name in self.get_source_tables():
                bronze_path = self.settings.get_bronze_path(table_name)
                logger.info(f"Loading bronze table: {table_name}")
                source_data[table_name] = self.delta_ops.read_delta(bronze_path)
            
            # Transform
            logger.info("Transforming data")
            transformed_df = self.transform(source_data)
            
            # Write to silver table
            silver_path = self.settings.get_silver_path(self.get_target_table())
            logger.info(f"Writing {len(transformed_df)} rows to {silver_path}")
            
            self.delta_ops.write_delta(
                transformed_df,
                silver_path,
                mode="overwrite"  # Silver tables are typically full refresh
            )
            
            return {
                "status": "success",
                "rows_processed": len(transformed_df),
                "message": f"Successfully processed {len(transformed_df)} rows"
            }
            
        except Exception as e:
            logger.error(f"Error in silver pipeline {self.get_name()}: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
                "message": f"Pipeline failed: {str(e)}"
            }


class BaseGoldPipeline(BasePipeline):
    """Base class for Gold layer pipelines (aggregation/business logic)."""
    
    @abstractmethod
    def get_source_tables(self) -> List[str]:
        """
        Get list of source table names (silver tables).
        
        Returns:
            List of table names
        """
        pass
    
    @abstractmethod
    def get_target_table(self) -> str:
        """Get target Delta table name."""
        pass
    
    @abstractmethod
    def transform(self, source_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Transform source data into target format.
        
        Args:
            source_data: Dictionary mapping table names to DataFrames
            
        Returns:
            Transformed DataFrame
        """
        pass
    
    def run(self, force: bool = False) -> Dict[str, Any]:
        """
        Run the gold pipeline.
        
        Args:
            force: Force reprocessing
            
        Returns:
            Execution statistics
        """
        logger.info(f"Running gold pipeline: {self.get_name()}")
        
        try:
            # Load source tables
            source_data = {}
            for table_name in self.get_source_tables():
                silver_path = self.settings.get_silver_path(table_name)
                logger.info(f"Loading silver table: {table_name}")
                source_data[table_name] = self.delta_ops.read_delta(silver_path)
            
            # Transform
            logger.info("Transforming data")
            transformed_df = self.transform(source_data)
            
            # Write to gold table
            gold_path = self.settings.get_gold_path(self.get_target_table())
            logger.info(f"Writing {len(transformed_df)} rows to {gold_path}")
            
            self.delta_ops.write_delta(
                transformed_df,
                gold_path,
                mode="overwrite"
            )
            
            return {
                "status": "success",
                "rows_processed": len(transformed_df),
                "message": f"Successfully processed {len(transformed_df)} rows"
            }
            
        except Exception as e:
            logger.error(f"Error in gold pipeline {self.get_name()}: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e)
            }

