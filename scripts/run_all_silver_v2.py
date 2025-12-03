#!/usr/bin/env python3
"""
Master script to execute all Silver V2 SQL pipelines in correct dependency order.

Order:
1. dim_commune (no dependencies)
2. dim_accueillant, dim_gare, dim_ligne (depend on dim_commune, can run in parallel)
3. dim_siae_structure (depends on dim_commune)
4. fact_logement, fact_zone_attraction (depend on dim_commune)
5. fact_siae_poste (depends on dim_siae_structure)
"""
import sys
from pathlib import Path
import logging
from datetime import datetime

# Add app directory to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import all pipelines
from app.pipelines.silver_v2.dim_commune import DimCommunePipeline
from app.pipelines.silver_v2.dim_accueillant import DimAccueillantPipeline
from app.pipelines.silver_v2.dim_gare import DimGarePipeline
from app.pipelines.silver_v2.dim_ligne import DimLignePipeline
from app.pipelines.silver_v2.dim_siae_structure import DimSIAEStructurePipeline
from app.pipelines.silver_v2.fact_logement import FactLogementPipeline
from app.pipelines.silver_v2.fact_zone_attraction import FactZoneAttractionPipeline
from app.pipelines.silver_v2.fact_siae_poste import FactSIAEPostePipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def run_pipeline(pipeline_class, name: str) -> dict:
    """Run a single pipeline and return results."""
    start_time = datetime.now()
    logger.info(f"\n{'='*60}")
    logger.info(f"🚀 Starting: {name}")
    logger.info(f"{'='*60}")
    
    try:
        pipeline = pipeline_class()
        result = pipeline.run(force=True)
        
        duration = (datetime.now() - start_time).total_seconds()
        rows = result.get('rows_processed', 0)
        
        logger.info(f"✅ {name} completed successfully")
        logger.info(f"   Rows processed: {rows:,}")
        logger.info(f"   Duration: {duration:.2f}s")
        
        return {
            'name': name,
            'status': 'success',
            'rows': rows,
            'duration': duration
        }
    except Exception as e:
        duration = (datetime.now() - start_time).total_seconds()
        logger.error(f"❌ {name} failed: {str(e)}")
        logger.exception(e)
        
        return {
            'name': name,
            'status': 'failed',
            'error': str(e),
            'duration': duration
        }


def main():
    """Execute all Silver V2 pipelines in dependency order."""
    logger.info("="*80)
    logger.info("🎯 SILVER V2 MIGRATION - SQL-BASED WITH DUCKDB")
    logger.info("="*80)
    
    overall_start = datetime.now()
    results = []
    
    # Phase 1: Foundation - dim_commune
    logger.info("\n📌 PHASE 1: Foundation Dimension")
    results.append(run_pipeline(DimCommunePipeline, "dim_commune"))
    
    # Phase 2: Other Dimensions
    logger.info("\n📌 PHASE 2: Other Dimensions")
    results.append(run_pipeline(DimAccueillantPipeline, "dim_accueillant"))
    results.append(run_pipeline(DimGarePipeline, "dim_gare"))
    results.append(run_pipeline(DimLignePipeline, "dim_ligne"))
    results.append(run_pipeline(DimSIAEStructurePipeline, "dim_siae_structure"))
    
    # Phase 3: Fact Tables
    logger.info("\n📌 PHASE 3: Fact Tables")
    results.append(run_pipeline(FactLogementPipeline, "fact_logement"))
    results.append(run_pipeline(FactZoneAttractionPipeline, "fact_zone_attraction"))
    results.append(run_pipeline(FactSIAEPostePipeline, "fact_siae_poste"))
    
    # Summary
    overall_duration = (datetime.now() - overall_start).total_seconds()
    
    logger.info("\n" + "="*80)
    logger.info("📊 EXECUTION SUMMARY")
    logger.info("="*80)
    
    successful = [r for r in results if r['status'] == 'success']
    failed = [r for r in results if r['status'] == 'failed']
    
    logger.info(f"\n✅ Successful: {len(successful)}/{len(results)}")
    for r in successful:
        logger.info(f"   - {r['name']}: {r['rows']:,} rows in {r['duration']:.2f}s")
    
    if failed:
        logger.info(f"\n❌ Failed: {len(failed)}/{len(results)}")
        for r in failed:
            logger.info(f"   - {r['name']}: {r.get('error', 'Unknown error')}")
    
    total_rows = sum(r['rows'] for r in successful)
    logger.info(f"\n📊 Total rows processed: {total_rows:,}")
    logger.info(f"⏱️  Total duration: {overall_duration:.2f}s")
    logger.info(f"⚡ Avg speed: {total_rows/overall_duration:.0f} rows/sec")
    
    logger.info("\n" + "="*80)
    if len(successful) == len(results):
        logger.info("🎉 ALL PIPELINES COMPLETED SUCCESSFULLY!")
        logger.info("="*80)
        logger.info("\n📝 Next steps:")
        logger.info("   1. Run validation tests: pytest tests/migration/ -v -s")
        logger.info("   2. Check API: GET /catalog/silver_v2")
        logger.info("   3. Review data: GET /preview/silver_v2/dim_commune")
        logger.info("   4. Deploy when ready: ./scripts/deploy.sh")
        return 0
    else:
        logger.info("⚠️  SOME PIPELINES FAILED - CHECK LOGS ABOVE")
        logger.info("="*80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
