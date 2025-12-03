"""
Validation script to compare silver vs silver_v2 data volumes.

This script:
1. Loads both silver and silver_v2 tables from GCS
2. Compares row counts per table
3. Compares unique key counts for main columns
4. Checks schema compatibility
5. Generates validation report with pass/fail status
"""
import sys
import logging
from typing import Dict, List, Tuple
from deltalake import DeltaTable
import pandas as pd
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SilverV2Validator:
    """Validator for Silver V2 migration."""
    
    # Table mapping: old_name -> new_name
    TABLE_MAPPING = {
        'geo': 'dim_commune',
        'accueillants': 'dim_accueillant',
        'gares': 'dim_gare',
        'lignes': 'dim_ligne',
        'siae_structures': 'dim_siae_structure',
        'logement': 'fact_logement',
        'zones_attraction': 'fact_zone_attraction',
        'siae_postes': 'fact_siae_poste'
    }
    
    # Expected surrogate keys per table
    SURROGATE_KEYS = {
        'dim_commune': 'commune_sk',
        'dim_accueillant': 'accueillant_sk',
        'dim_gare': 'gare_sk',
        'dim_ligne': 'ligne_sk',
        'dim_siae_structure': 'siae_structure_sk',
        'fact_logement': 'logement_sk',
        'fact_zone_attraction': 'zone_attraction_sk',
        'fact_siae_poste': 'siae_poste_sk'
    }
    
    # Expected foreign keys
    FOREIGN_KEYS = {
        'dim_accueillant': ['commune_sk'],
        'dim_gare': ['commune_sk'],
        'dim_siae_structure': ['commune_sk'],
        'fact_logement': ['commune_sk'],
        'fact_zone_attraction': ['commune_sk', 'commune_pole_sk'],
        'fact_siae_poste': ['siae_structure_sk']
    }
    
    # Required metadata columns
    METADATA_COLUMNS = [
        'job_insert_id',
        'job_insert_date_utc',
        'job_modify_id',
        'job_modify_date_utc'
    ]
    
    def __init__(self, base_path: str = "gs://jaccueille/delta"):
        self.base_path = base_path
        self.results = []
        self.errors = []
    
    def load_table(self, layer: str, table: str) -> pd.DataFrame:
        """Load a Delta table from GCS."""
        path = f"{self.base_path}/{layer}/{table}"
        try:
            dt = DeltaTable(path)
            df = dt.to_pandas()
            logger.info(f"Loaded {layer}.{table}: {len(df)} rows")
            return df
        except Exception as e:
            logger.error(f"Failed to load {layer}.{table}: {e}")
            raise
    
    def validate_row_counts(self, old_table: str, new_table: str, 
                           old_df: pd.DataFrame, new_df: pd.DataFrame) -> Dict:
        """Compare row counts between old and new tables."""
        old_count = len(old_df)
        new_count = len(new_df)
        diff = new_count - old_count
        diff_pct = (diff / old_count * 100) if old_count > 0 else 0
        
        # For dim_accueillant, we expect reduction due to deduplication
        if new_table == 'dim_accueillant':
            acceptable = diff < 0 and abs(diff_pct) < 30  # Allow up to 30% reduction
        else:
            acceptable = abs(diff_pct) < 10  # Allow 10% variance
        
        result = {
            'test': 'Row Count Comparison',
            'old_table': old_table,
            'new_table': new_table,
            'old_count': old_count,
            'new_count': new_count,
            'difference': diff,
            'difference_pct': round(diff_pct, 2),
            'status': 'PASS' if acceptable else 'FAIL',
            'message': f"{old_table} ({old_count}) → {new_table} ({new_count}), diff: {diff} ({diff_pct:.1f}%)"
        }
        
        self.results.append(result)
        return result
    
    def validate_surrogate_key(self, table: str, df: pd.DataFrame) -> Dict:
        """Validate surrogate key is unique and non-null."""
        sk_column = self.SURROGATE_KEYS.get(table)
        
        if not sk_column:
            return {'status': 'SKIP', 'message': f'No surrogate key defined for {table}'}
        
        if sk_column not in df.columns:
            result = {
                'test': 'Surrogate Key Validation',
                'table': table,
                'key_column': sk_column,
                'status': 'FAIL',
                'message': f'Surrogate key {sk_column} not found in {table}'
            }
            self.results.append(result)
            return result
        
        total = len(df)
        unique = df[sk_column].nunique()
        nulls = df[sk_column].isnull().sum()
        
        passed = (unique == total) and (nulls == 0)
        
        result = {
            'test': 'Surrogate Key Validation',
            'table': table,
            'key_column': sk_column,
            'total_rows': total,
            'unique_values': unique,
            'null_count': nulls,
            'status': 'PASS' if passed else 'FAIL',
            'message': f'{table}.{sk_column}: {unique}/{total} unique, {nulls} nulls'
        }
        
        self.results.append(result)
        return result
    
    def validate_metadata_columns(self, table: str, df: pd.DataFrame) -> Dict:
        """Validate all metadata columns are present."""
        missing = [col for col in self.METADATA_COLUMNS if col not in df.columns]
        
        result = {
            'test': 'Metadata Columns',
            'table': table,
            'required_columns': self.METADATA_COLUMNS,
            'missing_columns': missing,
            'status': 'PASS' if not missing else 'FAIL',
            'message': f'{table}: All metadata present' if not missing else f'{table}: Missing {missing}'
        }
        
        self.results.append(result)
        return result
    
    def validate_foreign_keys(self, table: str, df: pd.DataFrame, 
                             dim_commune_df: pd.DataFrame = None,
                             dim_siae_structure_df: pd.DataFrame = None) -> Dict:
        """Validate foreign key relationships."""
        fks = self.FOREIGN_KEYS.get(table, [])
        
        if not fks:
            return {'status': 'SKIP', 'message': f'No foreign keys defined for {table}'}
        
        all_valid = True
        messages = []
        
        for fk in fks:
            if fk not in df.columns:
                all_valid = False
                messages.append(f'FK {fk} not found')
                continue
            
            # Check for nulls (some FKs are optional)
            fk_values = df[fk].dropna()
            
            if fk == 'commune_sk' and dim_commune_df is not None:
                valid_keys = set(dim_commune_df['commune_sk'].unique())
                invalid = fk_values[~fk_values.isin(valid_keys)]
                if len(invalid) > 0:
                    all_valid = False
                    messages.append(f'{fk}: {len(invalid)} orphaned values')
                else:
                    messages.append(f'{fk}: All {len(fk_values)} values valid')
            
            elif fk == 'commune_pole_sk' and dim_commune_df is not None:
                valid_keys = set(dim_commune_df['commune_sk'].unique())
                invalid = fk_values[~fk_values.isin(valid_keys)]
                if len(invalid) > 0:
                    all_valid = False
                    messages.append(f'{fk}: {len(invalid)} orphaned values')
                else:
                    messages.append(f'{fk}: All {len(fk_values)} values valid')
            
            elif fk == 'siae_structure_sk' and dim_siae_structure_df is not None:
                valid_keys = set(dim_siae_structure_df['siae_structure_sk'].unique())
                invalid = fk_values[~fk_values.isin(valid_keys)]
                if len(invalid) > 0:
                    all_valid = False
                    messages.append(f'{fk}: {len(invalid)} orphaned values')
                else:
                    messages.append(f'{fk}: All {len(fk_values)} values valid')
        
        result = {
            'test': 'Foreign Key Validation',
            'table': table,
            'foreign_keys': fks,
            'status': 'PASS' if all_valid else 'FAIL',
            'message': f'{table}: {"; ".join(messages)}'
        }
        
        self.results.append(result)
        return result
    
    def run_validation(self) -> bool:
        """Run full validation suite."""
        logger.info("="*80)
        logger.info("SILVER V2 VALIDATION REPORT")
        logger.info("="*80)
        logger.info(f"Started at: {datetime.now().isoformat()}")
        logger.info("")
        
        try:
            # Load dim_commune first (needed for FK validation)
            logger.info("Loading dimension tables for FK validation...")
            dim_commune_df = self.load_table('silver_v2', 'dim_commune')
            dim_siae_structure_df = self.load_table('silver_v2', 'dim_siae_structure')
            
            # Validate each table pair
            for old_table, new_table in self.TABLE_MAPPING.items():
                logger.info("")
                logger.info(f"Validating: {old_table} → {new_table}")
                logger.info("-"*80)
                
                try:
                    # Load tables
                    old_df = self.load_table('silver', old_table)
                    new_df = self.load_table('silver_v2', new_table)
                    
                    # Run validations
                    self.validate_row_counts(old_table, new_table, old_df, new_df)
                    self.validate_surrogate_key(new_table, new_df)
                    self.validate_metadata_columns(new_table, new_df)
                    self.validate_foreign_keys(new_table, new_df, dim_commune_df, dim_siae_structure_df)
                    
                except Exception as e:
                    error_msg = f"Error validating {old_table} → {new_table}: {e}"
                    logger.error(error_msg)
                    self.errors.append(error_msg)
                    self.results.append({
                        'test': 'Table Validation',
                        'old_table': old_table,
                        'new_table': new_table,
                        'status': 'ERROR',
                        'message': str(e)
                    })
            
            # Print summary
            self.print_summary()
            
            # Return overall pass/fail
            failed = sum(1 for r in self.results if r.get('status') == 'FAIL')
            return failed == 0
            
        except Exception as e:
            logger.error(f"Validation failed with error: {e}", exc_info=True)
            self.errors.append(str(e))
            return False
    
    def print_summary(self):
        """Print validation summary."""
        logger.info("")
        logger.info("="*80)
        logger.info("VALIDATION SUMMARY")
        logger.info("="*80)
        
        passed = sum(1 for r in self.results if r.get('status') == 'PASS')
        failed = sum(1 for r in self.results if r.get('status') == 'FAIL')
        skipped = sum(1 for r in self.results if r.get('status') == 'SKIP')
        errors = sum(1 for r in self.results if r.get('status') == 'ERROR')
        
        logger.info(f"Total Tests: {len(self.results)}")
        logger.info(f"  ✓ Passed: {passed}")
        logger.info(f"  ✗ Failed: {failed}")
        logger.info(f"  ⊘ Skipped: {skipped}")
        logger.info(f"  ⚠ Errors: {errors}")
        logger.info("")
        
        if failed > 0:
            logger.info("FAILED TESTS:")
            for result in self.results:
                if result.get('status') == 'FAIL':
                    logger.info(f"  ✗ {result.get('message', result)}")
            logger.info("")
        
        if errors > 0:
            logger.info("ERRORS:")
            for result in self.results:
                if result.get('status') == 'ERROR':
                    logger.info(f"  ⚠ {result.get('message', result)}")
            logger.info("")
        
        logger.info("DETAILED RESULTS:")
        for result in self.results:
            status_icon = {'PASS': '✓', 'FAIL': '✗', 'SKIP': '⊘', 'ERROR': '⚠'}.get(result.get('status'), '?')
            logger.info(f"  {status_icon} {result.get('message', result)}")
        
        logger.info("")
        logger.info("="*80)
        if failed == 0 and errors == 0:
            logger.info("✓ VALIDATION PASSED - Ready for cutover")
        else:
            logger.info("✗ VALIDATION FAILED - Fix issues before cutover")
        logger.info("="*80)


if __name__ == "__main__":
    validator = SilverV2Validator()
    success = validator.run_validation()
    
    sys.exit(0 if success else 1)

