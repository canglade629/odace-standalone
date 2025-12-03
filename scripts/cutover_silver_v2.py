"""
Run all silver_v2 pipelines to deploy to production silver layer.

This script runs the cutover - deploying silver_v2 pipelines to overwrite
the current silver layer with the new normalized schema.
"""
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import all silver pipelines (now pointing to silver_v2)
from app.pipelines.silver_v2.dim_commune import DimCommunePipeline
from app.pipelines.silver_v2.dim_accueillant import DimAccueillantPipeline
from app.pipelines.silver_v2.dim_gare import DimGarePipeline
from app.pipelines.silver_v2.dim_ligne import DimLignePipeline
from app.pipelines.silver_v2.dim_siae_structure import DimSIAEStructurePipeline
from app.pipelines.silver_v2.fact_logement import FactLogementPipeline
from app.pipelines.silver_v2.fact_zone_attraction import FactZoneAttractionPipeline
from app.pipelines.silver_v2.fact_siae_poste import FactSIAEPostePipeline


def run_silver_cutover():
    """Execute cutover - deploy silver_v2 to silver layer."""
    logger.info("="*80)
    logger.info("🚀 SILVER V2 CUTOVER - DEPLOYING TO PRODUCTION SILVER LAYER")
    logger.info("="*80)
    logger.info(f"Started at: {datetime.now().isoformat()}")
    logger.info("")
    
    # Define execution order (respecting dependencies)
    pipelines = [
        ("dim_commune (geo)", DimCommunePipeline),
        ("dim_accueillant (accueillants)", DimAccueillantPipeline),
        ("dim_gare (gares)", DimGarePipeline),
        ("dim_ligne (lignes)", DimLignePipeline),
        ("dim_siae_structure (siae_structures)", DimSIAEStructurePipeline),
        ("fact_logement (logement)", FactLogementPipeline),
        ("fact_zone_attraction (zones_attraction)", FactZoneAttractionPipeline),
        ("fact_siae_poste (siae_postes)", FactSIAEPostePipeline),
    ]
    
    results = []
    total_rows = 0
    start_time = datetime.now()
    
    for name, PipelineClass in pipelines:
        logger.info("")
        logger.info(f"🔄 Running: {name}")
        logger.info("-"*80)
        
        try:
            pipeline = PipelineClass()
            result = pipeline.run(force=True)
            
            if result.get("status") == "success":
                rows = result.get("rows_processed", 0)
                total_rows += rows
                logger.info(f"✅ {name}: {rows:,} rows")
                results.append((name, "SUCCESS", rows))
            else:
                logger.error(f"❌ {name}: {result.get('message', 'Unknown error')}")
                results.append((name, "FAILED", 0))
        
        except Exception as e:
            logger.error(f"❌ {name}: {str(e)}", exc_info=True)
            results.append((name, "ERROR", 0))
    
    # Summary
    duration = (datetime.now() - start_time).total_seconds()
    success_count = sum(1 for _, status, _ in results if status == "SUCCESS")
    fail_count = len(results) - success_count
    
    logger.info("")
    logger.info("="*80)
    logger.info("📊 CUTOVER SUMMARY")
    logger.info("="*80)
    logger.info(f"Total Pipelines: {len(results)}")
    logger.info(f"  ✅ Successful: {success_count}")
    logger.info(f"  ❌ Failed: {fail_count}")
    logger.info(f"Total Rows: {total_rows:,}")
    logger.info(f"Duration: {duration:.2f}s")
    logger.info("")
    
    for name, status, rows in results:
        icon = "✅" if status == "SUCCESS" else "❌"
        logger.info(f"  {icon} {name}: {rows:,} rows" if status == "SUCCESS" else f"  {icon} {name}: {status}")
    
    logger.info("")
    logger.info("="*80)
    if fail_count == 0:
        logger.info("🎉 CUTOVER COMPLETE - All pipelines deployed successfully!")
        logger.info("="*80)
        logger.info("")
        logger.info("Next steps:")
        logger.info("  1. Test API endpoints: GET /api/data/catalog/silver")
        logger.info("  2. Verify data in GCS: gs://jaccueille/delta/silver/")
        logger.info("  3. Update documentation")
        return 0
    else:
        logger.info("⚠️  CUTOVER INCOMPLETE - Some pipelines failed")
        logger.info("="*80)
        logger.info("")
        logger.info("Please review errors above and:")
        logger.info("  1. Fix any issues")
        logger.info("  2. Re-run failed pipelines")
        logger.info("  3. Or rollback using: gsutil -m cp -r gs://jaccueille/delta/silver_v1_backup/* gs://jaccueille/delta/silver/")
        return 1


if __name__ == "__main__":
    exit_code = run_silver_cutover()
    sys.exit(exit_code)

