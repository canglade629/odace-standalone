"""Migration validation utilities for comparing V1 and V2 silver tables."""
import logging
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from deltalake import DeltaTable
from app.core.config import get_settings
import hashlib

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of a single validation check."""
    
    def __init__(self, name: str, passed: bool, message: str, details: Optional[Dict[str, Any]] = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details or {}
    
    def __repr__(self):
        status = "✅ PASS" if self.passed else "❌ FAIL"
        return f"{status}: {self.name} - {self.message}"


class MigrationValidator:
    """Validator for comparing old and new silver tables during migration."""
    
    def __init__(self):
        self.settings = get_settings()
        self.results: List[ValidationResult] = []
    
    def _load_table(self, layer: str, table_name: str) -> pd.DataFrame:
        """Load a Delta table from GCS.
        
        Args:
            layer: Layer name (silver or silver_v2)
            table_name: Table name
            
        Returns:
            DataFrame with table data
        """
        if layer == "silver":
            path = self.settings.get_silver_path(table_name)
        elif layer == "silver_v2":
            path = self.settings.get_silver_v2_path(table_name)
        else:
            raise ValueError(f"Invalid layer: {layer}")
        
        logger.info(f"Loading table from {path}")
        dt = DeltaTable(path)
        df = dt.to_pandas()
        logger.info(f"Loaded {len(df)} rows from {layer}.{table_name}")
        return df
    
    def compare_row_counts(self, old_table: str, new_table: str, 
                          old_layer: str = "silver", 
                          new_layer: str = "silver_v2") -> ValidationResult:
        """Compare row counts between old and new tables.
        
        Args:
            old_table: Name of old table
            new_table: Name of new table
            old_layer: Layer of old table (default: silver)
            new_layer: Layer of new table (default: silver_v2)
            
        Returns:
            ValidationResult
        """
        try:
            old_df = self._load_table(old_layer, old_table)
            new_df = self._load_table(new_layer, new_table)
            
            old_count = len(old_df)
            new_count = len(new_df)
            
            passed = old_count == new_count
            message = f"Old: {old_count} rows, New: {new_count} rows"
            
            result = ValidationResult(
                name=f"Row count: {old_table} → {new_table}",
                passed=passed,
                message=message,
                details={"old_count": old_count, "new_count": new_count, "diff": new_count - old_count}
            )
            self.results.append(result)
            return result
            
        except Exception as e:
            logger.error(f"Error comparing row counts: {e}", exc_info=True)
            result = ValidationResult(
                name=f"Row count: {old_table} → {new_table}",
                passed=False,
                message=f"Error: {str(e)}"
            )
            self.results.append(result)
            return result
    
    def compare_unique_values(self, old_table: str, old_column: str,
                             new_table: str, new_column: str,
                             old_layer: str = "silver",
                             new_layer: str = "silver_v2") -> ValidationResult:
        """Compare unique values between old and new columns.
        
        Args:
            old_table: Name of old table
            old_column: Column name in old table
            new_table: Name of new table
            new_column: Column name in new table
            old_layer: Layer of old table
            new_layer: Layer of new table
            
        Returns:
            ValidationResult
        """
        try:
            old_df = self._load_table(old_layer, old_table)
            new_df = self._load_table(new_layer, new_table)
            
            old_values = set(old_df[old_column].dropna().unique())
            new_values = set(new_df[new_column].dropna().unique())
            
            missing_in_new = old_values - new_values
            added_in_new = new_values - old_values
            
            passed = len(missing_in_new) == 0
            
            if passed:
                message = f"All {len(old_values)} unique values preserved"
            else:
                message = f"Missing {len(missing_in_new)} values in new table"
            
            result = ValidationResult(
                name=f"Unique values: {old_table}.{old_column} → {new_table}.{new_column}",
                passed=passed,
                message=message,
                details={
                    "old_unique_count": len(old_values),
                    "new_unique_count": len(new_values),
                    "missing_count": len(missing_in_new),
                    "added_count": len(added_in_new),
                    "missing_samples": list(missing_in_new)[:10] if missing_in_new else [],
                    "added_samples": list(added_in_new)[:10] if added_in_new else []
                }
            )
            self.results.append(result)
            return result
            
        except Exception as e:
            logger.error(f"Error comparing unique values: {e}", exc_info=True)
            result = ValidationResult(
                name=f"Unique values: {old_table}.{old_column} → {new_table}.{new_column}",
                passed=False,
                message=f"Error: {str(e)}"
            )
            self.results.append(result)
            return result
    
    def validate_no_nulls(self, table: str, columns: List[str],
                         layer: str = "silver_v2") -> ValidationResult:
        """Validate that specified columns have no NULL values.
        
        Args:
            table: Table name
            columns: List of column names to check
            layer: Layer name (default: silver_v2)
            
        Returns:
            ValidationResult
        """
        try:
            df = self._load_table(layer, table)
            
            null_counts = {}
            for col in columns:
                if col in df.columns:
                    null_count = df[col].isna().sum()
                    if null_count > 0:
                        null_counts[col] = null_count
                else:
                    null_counts[col] = f"Column not found"
            
            passed = len(null_counts) == 0
            
            if passed:
                message = f"No NULLs found in {len(columns)} required columns"
            else:
                message = f"Found NULLs in {len(null_counts)} columns: {list(null_counts.keys())}"
            
            result = ValidationResult(
                name=f"No NULLs: {table}",
                passed=passed,
                message=message,
                details={"null_counts": null_counts}
            )
            self.results.append(result)
            return result
            
        except Exception as e:
            logger.error(f"Error validating NULLs: {e}", exc_info=True)
            result = ValidationResult(
                name=f"No NULLs: {table}",
                passed=False,
                message=f"Error: {str(e)}"
            )
            self.results.append(result)
            return result
    
    def validate_unique_key(self, table: str, key_column: str,
                           layer: str = "silver_v2") -> ValidationResult:
        """Validate that a key column has all unique values.
        
        Args:
            table: Table name
            key_column: Column name to check for uniqueness
            layer: Layer name (default: silver_v2)
            
        Returns:
            ValidationResult
        """
        try:
            df = self._load_table(layer, table)
            
            if key_column not in df.columns:
                result = ValidationResult(
                    name=f"Unique key: {table}.{key_column}",
                    passed=False,
                    message=f"Column {key_column} not found"
                )
                self.results.append(result)
                return result
            
            total_count = len(df)
            unique_count = df[key_column].nunique()
            null_count = df[key_column].isna().sum()
            
            passed = (total_count == unique_count) and (null_count == 0)
            
            if passed:
                message = f"All {total_count} values are unique and non-NULL"
            else:
                duplicates = total_count - unique_count
                message = f"Found {duplicates} duplicates and {null_count} NULLs"
            
            result = ValidationResult(
                name=f"Unique key: {table}.{key_column}",
                passed=passed,
                message=message,
                details={
                    "total_count": total_count,
                    "unique_count": unique_count,
                    "null_count": null_count,
                    "duplicate_count": total_count - unique_count
                }
            )
            self.results.append(result)
            return result
            
        except Exception as e:
            logger.error(f"Error validating unique key: {e}", exc_info=True)
            result = ValidationResult(
                name=f"Unique key: {table}.{key_column}",
                passed=False,
                message=f"Error: {str(e)}"
            )
            self.results.append(result)
            return result
    
    def validate_foreign_keys(self, fact_table: str, fk_column: str,
                             dim_table: str, pk_column: str,
                             fact_layer: str = "silver_v2",
                             dim_layer: str = "silver_v2") -> ValidationResult:
        """Validate foreign key relationships.
        
        Args:
            fact_table: Fact table name
            fk_column: Foreign key column name
            dim_table: Dimension table name
            pk_column: Primary key column name
            fact_layer: Layer of fact table
            dim_layer: Layer of dimension table
            
        Returns:
            ValidationResult
        """
        try:
            fact_df = self._load_table(fact_layer, fact_table)
            dim_df = self._load_table(dim_layer, dim_table)
            
            # Get FK values (excluding NULLs)
            fk_values = set(fact_df[fk_column].dropna().unique())
            pk_values = set(dim_df[pk_column].dropna().unique())
            
            # Find orphaned FKs
            orphaned = fk_values - pk_values
            
            passed = len(orphaned) == 0
            
            if passed:
                message = f"All {len(fk_values)} FK values valid"
            else:
                message = f"Found {len(orphaned)} orphaned FK values"
            
            result = ValidationResult(
                name=f"FK: {fact_table}.{fk_column} → {dim_table}.{pk_column}",
                passed=passed,
                message=message,
                details={
                    "fk_count": len(fk_values),
                    "pk_count": len(pk_values),
                    "orphaned_count": len(orphaned),
                    "orphaned_samples": list(orphaned)[:10] if orphaned else []
                }
            )
            self.results.append(result)
            return result
            
        except Exception as e:
            logger.error(f"Error validating foreign keys: {e}", exc_info=True)
            result = ValidationResult(
                name=f"FK: {fact_table}.{fk_column} → {dim_table}.{pk_column}",
                passed=False,
                message=f"Error: {str(e)}"
            )
            self.results.append(result)
            return result
    
    def validate_metadata_columns(self, table: str, layer: str = "silver_v2") -> ValidationResult:
        """Validate that all 4 required metadata columns exist and are populated.
        
        Args:
            table: Table name
            layer: Layer name (default: silver_v2)
            
        Returns:
            ValidationResult
        """
        required_columns = [
            'job_insert_id',
            'job_insert_date_utc',
            'job_modify_id',
            'job_modify_date_utc'
        ]
        
        try:
            df = self._load_table(layer, table)
            
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                result = ValidationResult(
                    name=f"Metadata columns: {table}",
                    passed=False,
                    message=f"Missing columns: {missing_columns}",
                    details={"missing_columns": missing_columns}
                )
                self.results.append(result)
                return result
            
            # Check for NULLs in metadata columns
            null_counts = {col: df[col].isna().sum() for col in required_columns}
            has_nulls = any(count > 0 for count in null_counts.values())
            
            passed = not has_nulls
            
            if passed:
                message = "All 4 metadata columns present and populated"
            else:
                message = f"Found NULLs in metadata columns: {null_counts}"
            
            result = ValidationResult(
                name=f"Metadata columns: {table}",
                passed=passed,
                message=message,
                details={"null_counts": null_counts}
            )
            self.results.append(result)
            return result
            
        except Exception as e:
            logger.error(f"Error validating metadata columns: {e}", exc_info=True)
            result = ValidationResult(
                name=f"Metadata columns: {table}",
                passed=False,
                message=f"Error: {str(e)}"
            )
            self.results.append(result)
            return result
    
    def generate_migration_report(self) -> Dict[str, Any]:
        """Generate a comprehensive migration report.
        
        Returns:
            Dictionary with validation results and statistics
        """
        total_validations = len(self.results)
        passed_validations = sum(1 for r in self.results if r.passed)
        failed_validations = total_validations - passed_validations
        
        report = {
            "summary": {
                "total_validations": total_validations,
                "passed": passed_validations,
                "failed": failed_validations,
                "success_rate": f"{(passed_validations / total_validations * 100):.1f}%" if total_validations > 0 else "N/A"
            },
            "validations": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "message": r.message,
                    "details": r.details
                }
                for r in self.results
            ],
            "failed_validations": [
                {
                    "name": r.name,
                    "message": r.message,
                    "details": r.details
                }
                for r in self.results if not r.passed
            ]
        }
        
        return report
    
    def print_report(self):
        """Print a formatted migration report to console."""
        report = self.generate_migration_report()
        
        print("\n" + "="*80)
        print("MIGRATION VALIDATION REPORT")
        print("="*80)
        print(f"\nTotal Validations: {report['summary']['total_validations']}")
        print(f"✅ Passed: {report['summary']['passed']}")
        print(f"❌ Failed: {report['summary']['failed']}")
        print(f"Success Rate: {report['summary']['success_rate']}")
        print("\n" + "-"*80)
        
        if report['failed_validations']:
            print("\n⚠️  FAILED VALIDATIONS:")
            print("-"*80)
            for failure in report['failed_validations']:
                print(f"\n❌ {failure['name']}")
                print(f"   {failure['message']}")
                if failure['details']:
                    for key, value in failure['details'].items():
                        print(f"   - {key}: {value}")
        
        print("\n" + "="*80)
        print("ALL VALIDATIONS:")
        print("="*80)
        for result in self.results:
            print(f"\n{result}")
        
        print("\n" + "="*80 + "\n")

