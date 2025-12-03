"""SQL-based base pipeline for Silver transformations using DuckDB."""
from app.pipelines.base_sql import SQLSilverPipeline
from abc import abstractmethod
import logging
import pandas as pd

logger = logging.getLogger(__name__)


class SQLSilverV2Pipeline(SQLSilverPipeline):
    """
    SQL-based Silver pipeline using DuckDB.
    
    Silver layer enforces:
    - Surrogate keys (_sk) on all tables
    - Metadata columns (job_insert_id, job_insert_date_utc, job_modify_id, job_modify_date_utc)
    - Proper naming conventions (dim_/fact_ prefixes, lowercase, underscores)
    - Normalized schema with proper foreign keys
    - SQL transformations for clarity and maintainability
    """
    
    @abstractmethod
    def get_target_table(self) -> str:
        """
        Get target table name (should start with dim_ or fact_).
        
        Returns:
            Table name (e.g., 'dim_commune', 'fact_logement')
        """
        pass
    
    @abstractmethod
    def get_sql_query(self) -> str:
        """
        Get SQL query for transformation.
        
        Reference bronze/silver tables, e.g.:
        - SELECT * FROM bronze_geo
        - SELECT * FROM silver_dim_commune
        
        Returns:
            SQL query string
        """
        pass
    
    def run(self, force: bool = False) -> dict:
        """Override run to write to silver path."""
        try:
            logger.info(f"Running silver pipeline: {self.get_name()}")
            
            # Transform (SQL-based, loads its own sources)
            logger.info("Transforming data")
            transformed_df = self.transform({})  # SQL pipelines don't use source_data parameter
            
            # Write to silver table
            table_name = self.get_target_table()
            target_path = self.settings.get_silver_path(table_name)
            logger.info(f"Writing {len(transformed_df)} rows to {target_path}")
            
            # Verify metadata columns
            required_metadata = [
                'job_insert_id',
                'job_insert_date_utc',
                'job_modify_id',
                'job_modify_date_utc'
            ]
            
            missing_metadata = [col for col in required_metadata if col not in transformed_df.columns]
            if missing_metadata:
                logger.warning(f"Missing metadata columns: {missing_metadata}")
            
            # Write to Delta
            from app.utils.delta_ops import DeltaOperations
            DeltaOperations.write_delta(
                df=transformed_df,
                table_path=target_path,
                mode="overwrite"  # For initial migration, overwrite
            )
            
            logger.info(f"Successfully loaded data to silver.{table_name}")
            
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
