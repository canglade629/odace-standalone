"""Delta Lake operations utilities."""
import pandas as pd
import pyarrow as pa
from deltalake import DeltaTable, write_deltalake
from typing import Optional, List, Dict, Any
import logging
from google.cloud import storage
from app.core.config import get_settings

logger = logging.getLogger(__name__)


class DeltaOperations:
    """Helper class for Delta Lake operations."""
    
    @staticmethod
    def read_delta(table_path: str, columns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Read a Delta table into a pandas DataFrame.
        
        Args:
            table_path: Path to Delta table (gs://bucket/path)
            columns: Optional list of columns to read
            
        Returns:
            pandas DataFrame
        """
        logger.info(f"Reading Delta table from {table_path}")
        dt = DeltaTable(table_path)
        df = dt.to_pandas(columns=columns)
        logger.info(f"Read {len(df)} rows from Delta table")
        return df
    
    @staticmethod
    def write_delta(
        df: pd.DataFrame,
        table_path: str,
        mode: str = "append",
        partition_by: Optional[List[str]] = None,
        schema_mode: str = "merge"
    ) -> None:
        """
        Write a pandas DataFrame to a Delta table with schema evolution support.
        
        Args:
            df: pandas DataFrame to write
            table_path: Path to Delta table
            mode: Write mode (append/overwrite)
            partition_by: Optional list of columns to partition by
            schema_mode: How to handle schema changes (merge/overwrite)
        """
        logger.info(f"Writing {len(df)} rows to Delta table at {table_path}")
        
        try:
            # Try writing with schema_mode first (works in newer deltalake versions)
            write_deltalake(
                table_path,
                df,
                mode=mode,
                partition_by=partition_by,
                schema_mode=schema_mode
            )
            logger.info(f"Successfully wrote to Delta table with schema_mode={schema_mode}")
        except TypeError as e:
            # If schema_mode not supported, fall back to basic write
            if "schema_mode" in str(e):
                logger.warning(f"schema_mode not supported, using basic write")
                try:
                    write_deltalake(
                        table_path,
                        df,
                        mode=mode,
                        partition_by=partition_by
                    )
                    logger.info(f"Successfully wrote to Delta table")
                except Exception as schema_error:
                    error_msg = str(schema_error)
                    logger.warning(f"Write failed with error: {type(schema_error).__name__}: {error_msg}")
                    if "Schema of data does not match" in error_msg or "schema" in error_msg.lower():
                        # Schema mismatch - need to delete table and recreate with new schema
                        logger.warning(f"Schema mismatch detected, deleting old table and creating with new schema")
                        try:
                            # Delete the existing table by loading it and using overwrite with engine='rust'
                            dt = DeltaTable(table_path)
                            logger.warning(f"Found existing table at version {dt.version()}, will replace with new schema")
                        except Exception:
                            logger.warning(f"No existing table found or couldn't load it")
                        
                        # Write with overwrite mode and schema_mode='overwrite' to force schema change
                        write_deltalake(
                            table_path,
                            df,
                            mode="overwrite",
                            partition_by=partition_by,
                            engine='rust',
                            overwrite_schema=True
                        )
                        logger.info(f"Successfully replaced Delta table with new schema")
                    else:
                        raise
            else:
                raise
        except Exception as e:
            # Handle schema mismatch errors with broadest exception catching
            error_msg = str(e)
            logger.warning(f"Write failed at top level with error: {type(e).__name__}: {error_msg}")
            if "Schema of data does not match" in error_msg or "schema" in error_msg.lower():
                # Schema mismatch - need to replace table with new schema
                logger.warning(f"Schema mismatch detected, replacing table with new schema")
                try:
                    dt = DeltaTable(table_path)
                    logger.warning(f"Found existing table at version {dt.version()}, will replace with new schema")
                except Exception:
                    logger.warning(f"No existing table found or couldn't load it")
                
                # Write with overwrite mode and overwrite_schema=True to force schema change
                write_deltalake(
                    table_path,
                    df,
                    mode="overwrite",
                    partition_by=partition_by,
                    engine='rust',
                    overwrite_schema=True
                )
                logger.info(f"Successfully replaced Delta table with new schema")
            else:
                raise
    
    @staticmethod
    def table_exists(table_path: str) -> bool:
        """
        Check if a Delta table exists.
        
        Args:
            table_path: Path to Delta table
            
        Returns:
            True if table exists, False otherwise
        """
        try:
            DeltaTable(table_path)
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_table_info(table_path: str) -> Dict[str, Any]:
        """
        Get information about a Delta table.
        
        Args:
            table_path: Path to Delta table
            
        Returns:
            Dictionary with table information
        """
        dt = DeltaTable(table_path)
        schema = dt.schema()
        
        return {
            "path": table_path,
            "version": dt.version(),
            "schema": schema.to_pydict(),
            "files": dt.files()
        }
    
    @staticmethod
    def optimize_table(table_path: str) -> None:
        """
        Optimize a Delta table (compact small files).
        
        Args:
            table_path: Path to Delta table
        """
        logger.info(f"Optimizing Delta table at {table_path}")
        dt = DeltaTable(table_path)
        # Note: optimize and vacuum are not yet available in deltalake Python
        # This is a placeholder for future implementation
        logger.warning("Table optimization not yet implemented in deltalake Python")
    
    @staticmethod
    def merge_delta(
        target_path: str,
        source_df: pd.DataFrame,
        merge_keys: List[str],
        update_cols: Optional[List[str]] = None,
        insert_cols: Optional[List[str]] = None
    ) -> Dict[str, int]:
        """
        Perform a merge (upsert) operation on a Delta table.
        
        This is a simplified merge that:
        1. Reads the target table
        2. Performs the merge in pandas
        3. Writes back with overwrite mode
        
        Args:
            target_path: Path to target Delta table
            source_df: Source DataFrame to merge
            merge_keys: Columns to use for matching
            update_cols: Columns to update on match (None = all)
            insert_cols: Columns to insert on no match (None = all)
            
        Returns:
            Dictionary with merge statistics
        """
        logger.info(f"Performing merge on Delta table at {target_path}")
        
        # Read target table if it exists
        if DeltaOperations.table_exists(target_path):
            target_df = DeltaOperations.read_delta(target_path)
            
            # Perform merge logic
            # Find matching rows
            merge_result = target_df.merge(
                source_df[merge_keys],
                on=merge_keys,
                how='outer',
                indicator=True
            )
            
            # Count operations
            updates = (merge_result['_merge'] == 'both').sum()
            inserts = (merge_result['_merge'] == 'right_only').sum()
            
            # Perform the actual merge
            # Remove rows from target that match
            non_matching = target_df[~target_df[merge_keys[0]].isin(source_df[merge_keys[0]])]
            # Combine with source (which includes updates and inserts)
            result_df = pd.concat([non_matching, source_df], ignore_index=True)
            
            stats = {"updated": updates, "inserted": inserts, "deleted": 0}
        else:
            # Table doesn't exist, just insert all
            result_df = source_df
            stats = {"updated": 0, "inserted": len(source_df), "deleted": 0}
        
        # Write the result
        DeltaOperations.write_delta(result_df, target_path, mode="overwrite")
        
        logger.info(f"Merge complete: {stats}")
        return stats
    
    @staticmethod
    def list_delta_tables(base_path: str) -> List[Dict[str, Any]]:
        """
        List all Delta tables under a given base path by scanning GCS.
        
        Args:
            base_path: Base path to scan (e.g., gs://bucket/delta/bronze)
            
        Returns:
            List of dictionaries with table information
        """
        logger.info(f"Scanning for Delta tables in {base_path}")
        settings = get_settings()
        
        # Parse GCS path
        path_parts = base_path.replace(f"gs://{settings.gcs_bucket}/", "")
        
        # Initialize GCS client
        client = storage.Client(project=settings.gcp_project_id)
        bucket = client.bucket(settings.gcs_bucket)
        
        # List all blobs with _delta_log directories
        blobs = client.list_blobs(settings.gcs_bucket, prefix=path_parts)
        
        # Find unique Delta tables by looking for _delta_log directories
        delta_tables = set()
        for blob in blobs:
            if "_delta_log/" in blob.name:
                # Extract table path (everything before _delta_log)
                table_path = blob.name.split("_delta_log/")[0].rstrip("/")
                delta_tables.add(table_path)
        
        # Get information about each table
        tables = []
        for table_path in sorted(delta_tables):
            full_path = f"gs://{settings.gcs_bucket}/{table_path}"
            # Extract table name (last part of path)
            table_name = table_path.split("/")[-1]
            
            try:
                dt = DeltaTable(full_path)
                tables.append({
                    "name": table_name,
                    "path": full_path,
                    "version": dt.version(),
                })
            except Exception as e:
                logger.warning(f"Could not read Delta table at {full_path}: {e}")
        
        logger.info(f"Found {len(tables)} Delta tables")
        return tables
    
    @staticmethod
    def get_table_schema(table_path: str) -> Dict[str, Any]:
        """
        Get schema information for a Delta table.
        
        Args:
            table_path: Path to Delta table
            
        Returns:
            Dictionary with schema information
        """
        logger.info(f"Getting schema for {table_path}")
        dt = DeltaTable(table_path)
        schema = dt.schema()
        
        # Convert schema to PyArrow schema for iteration
        # The delta-rs schema needs to be converted to PyArrow schema
        arrow_schema = schema.to_pyarrow()
        
        # Convert PyArrow schema to a more readable format
        fields = []
        for field in arrow_schema:
            fields.append({
                "name": field.name,
                "type": str(field.type),
                "nullable": field.nullable
            })
        
        # Get row count by reading the table
        try:
            df = dt.to_pandas()
            row_count = len(df)
        except Exception as e:
            logger.warning(f"Could not get row count: {e}")
            row_count = None
        
        return {
            "fields": fields,
            "version": dt.version(),
            "row_count": row_count,
            "num_fields": len(fields)
        }
    
    @staticmethod
    def preview_table(
        table_path: str,
        limit: int = 100,
        filters: Optional[List[Dict[str, str]]] = None,
        sort_by: Optional[str] = None,
        sort_order: str = "asc"
    ) -> Dict[str, Any]:
        """
        Get a preview of table data with optional filtering and sorting.
        
        Args:
            table_path: Path to Delta table
            limit: Maximum number of rows to return
            filters: List of filter dictionaries with 'column', 'operator', 'value'
            sort_by: Column to sort by
            sort_order: Sort order ('asc' or 'desc')
            
        Returns:
            Dictionary with preview data and metadata
        """
        logger.info(f"Previewing table {table_path} (limit={limit})")
        
        dt = DeltaTable(table_path)
        df = dt.to_pandas()
        
        total_rows = len(df)
        
        # Apply filters if provided
        if filters:
            for filter_spec in filters:
                column = filter_spec.get("column")
                operator = filter_spec.get("operator", "=")
                value = filter_spec.get("value")
                
                if column and column in df.columns:
                    try:
                        if operator == "=":
                            df = df[df[column] == value]
                        elif operator == "!=":
                            df = df[df[column] != value]
                        elif operator == "contains":
                            df = df[df[column].astype(str).str.contains(value, case=False, na=False)]
                        elif operator == ">":
                            df = df[df[column] > float(value)]
                        elif operator == "<":
                            df = df[df[column] < float(value)]
                        elif operator == ">=":
                            df = df[df[column] >= float(value)]
                        elif operator == "<=":
                            df = df[df[column] <= float(value)]
                    except Exception as e:
                        logger.warning(f"Filter failed for {column} {operator} {value}: {e}")
        
        filtered_rows = len(df)
        
        # Apply sorting if provided
        if sort_by and sort_by in df.columns:
            ascending = (sort_order.lower() == "asc")
            df = df.sort_values(by=sort_by, ascending=ascending)
        
        # Limit rows
        df_preview = df.head(limit)
        
        # Convert to records for JSON serialization
        # Handle datetime and other special types
        df_preview = df_preview.copy()
        for col in df_preview.columns:
            if pd.api.types.is_datetime64_any_dtype(df_preview[col]):
                df_preview[col] = df_preview[col].astype(str)
        
        records = df_preview.to_dict(orient="records")
        columns = list(df_preview.columns)
        
        return {
            "columns": columns,
            "data": records,
            "total_rows": total_rows,
            "filtered_rows": filtered_rows,
            "preview_rows": len(records)
        }


def get_delta_operations() -> DeltaOperations:
    """Get Delta operations instance."""
    return DeltaOperations()

