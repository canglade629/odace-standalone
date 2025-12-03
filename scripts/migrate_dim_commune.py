#!/usr/bin/env python3
"""Script to execute dim_commune migration and run validation tests."""
import sys
import os
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.pipelines.silver_v2.dim_commune import DimCommunePipeline
from app.utils.migration_validator import MigrationValidator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Execute dim_commune migration."""
    logger.info("="*80)
    logger.info("STARTING DIM_COMMUNE MIGRATION")
    logger.info("="*80)
    
    try:
        # Initialize and run pipeline
        logger.info("\n1. Running dim_commune pipeline...")
        pipeline = DimCommunePipeline()
        result = pipeline.run(force=True)
        
        logger.info(f"\nPipeline execution result:")
        logger.info(f"  - Rows processed: {result.get('rows_processed', 'N/A')}")
        logger.info(f"  - Files processed: {result.get('files_processed', 'N/A')}")
        
        if result.get('errors'):
            logger.error(f"  - Errors: {result['errors']}")
            return 1
        
        logger.info("\n✅ Pipeline executed successfully!")
        
        # Run validation tests
        logger.info("\n" + "="*80)
        logger.info("2. Running validation tests...")
        logger.info("="*80 + "\n")
        
        validator = MigrationValidator()
        
        # Test 1: Row count
        logger.info("Test 1: Row count comparison...")
        result1 = validator.compare_row_counts("geo", "dim_commune")
        logger.info(f"  {result1}")
        
        # Test 2: INSEE codes preserved
        logger.info("\nTest 2: INSEE codes preserved...")
        result2 = validator.compare_unique_values("geo", "CODGEO", "dim_commune", "commune_code")
        logger.info(f"  {result2}")
        
        # Test 3: Unique SK
        logger.info("\nTest 3: Surrogate key uniqueness...")
        result3 = validator.validate_unique_key("dim_commune", "commune_sk")
        logger.info(f"  {result3}")
        
        # Test 4: No NULLs
        logger.info("\nTest 4: No NULLs in required columns...")
        result4 = validator.validate_no_nulls("dim_commune", 
            ['commune_sk', 'commune_code', 'commune_label', 'departement_code'])
        logger.info(f"  {result4}")
        
        # Test 5: Metadata columns
        logger.info("\nTest 5: Metadata columns...")
        result5 = validator.validate_metadata_columns("dim_commune")
        logger.info(f"  {result5}")
        
        # Print full report
        logger.info("\n" + "="*80)
        logger.info("VALIDATION SUMMARY")
        logger.info("="*80)
        validator.print_report()
        
        # Check if all tests passed
        all_passed = all([result1.passed, result2.passed, result3.passed, result4.passed, result5.passed])
        
        if all_passed:
            logger.info("\n✅ ALL VALIDATIONS PASSED!")
            logger.info("dim_commune migration is complete and validated.")
            return 0
        else:
            logger.error("\n❌ SOME VALIDATIONS FAILED!")
            logger.error("Please review the report above.")
            return 1
            
    except Exception as e:
        logger.error(f"\n❌ Error during migration: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

