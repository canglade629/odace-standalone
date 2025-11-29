"""SQL execution using DuckDB with Delta Lake support."""
import duckdb
import pandas as pd
from typing import Optional, Dict, Any
import logging
from app.utils.delta_ops import DeltaOperations

logger = logging.getLogger(__name__)


class SQLExecutor:
    """Execute SQL queries using DuckDB with Delta Lake support."""
    
    def __init__(self):
        """Initialize DuckDB connection."""
        self.conn = duckdb.connect(":memory:")
        # Install and load delta extension
        try:
            self.conn.execute("INSTALL delta")
            self.conn.execute("LOAD delta")
            logger.info("DuckDB Delta extension loaded")
        except Exception as e:
            logger.warning(f"Could not load Delta extension: {e}")
    
    def register_delta_table(self, table_name: str, delta_path: str) -> None:
        """
        Register a Delta table for SQL queries.
        
        Args:
            table_name: Name to use in SQL queries
            delta_path: Path to Delta table (gs://...)
        """
        try:
            # Read Delta table as pandas DataFrame
            df = DeltaOperations.read_delta(delta_path)
            # Register as DuckDB table
            self.conn.register(table_name, df)
            logger.info(f"Registered Delta table {table_name} from {delta_path}")
        except Exception as e:
            logger.error(f"Failed to register table {table_name}: {e}")
            raise
    
    def execute_query(self, query: str) -> pd.DataFrame:
        """
        Execute a SQL query and return results.
        
        Args:
            query: SQL query to execute
            
        Returns:
            Query results as pandas DataFrame
        """
        logger.info(f"Executing SQL query")
        logger.debug(f"Query: {query}")
        
        result = self.conn.execute(query).fetchdf()
        logger.info(f"Query returned {len(result)} rows")
        return result
    
    def execute_merge(
        self,
        target_table: str,
        source_table: str,
        merge_condition: str,
        update_set: Dict[str, str],
        insert_columns: list,
        insert_values: list
    ) -> pd.DataFrame:
        """
        Execute a MERGE statement (simulated in DuckDB).
        
        Since DuckDB doesn't support MERGE directly, we simulate it with INSERT/UPDATE logic.
        
        Args:
            target_table: Target table name
            source_table: Source table name
            merge_condition: Join condition
            update_set: Dictionary of column -> expression for updates
            insert_columns: List of columns for insert
            insert_values: List of values/expressions for insert
            
        Returns:
            Merged DataFrame
        """
        # This is a simplified approach - for complex merges, 
        # we'll handle the logic in Python/pandas
        
        # Get source and target
        source_df = self.conn.execute(f"SELECT * FROM {source_table}").fetchdf()
        
        try:
            target_df = self.conn.execute(f"SELECT * FROM {target_table}").fetchdf()
        except:
            # Target doesn't exist, just return source
            return source_df
        
        # For now, return source - the actual merge logic will be in pipeline classes
        return source_df
    
    def close(self):
        """Close the DuckDB connection."""
        self.conn.close()


def get_sql_executor() -> SQLExecutor:
    """Get a new SQL executor instance."""
    return SQLExecutor()

