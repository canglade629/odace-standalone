# Quick Start: Testing Silver V2 (Replacement) Pipelines

## Overview

Silver V2 has **replaced** the old silver layer. The API endpoints remain the same, but now run V2 pipelines with the new schema.

## 1. Deploy to Cloud Run

```bash
cd /Users/christophe.anglade/Documents/odace_backend
./scripts/deploy.sh
```

## 2. Test Pipelines

### List Silver Pipelines (Now V2)

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://odace-pipeline-588398598428.europe-west1.run.app/api/pipeline/list?layer=silver
```

**Expected**: 8 pipelines (geo, accueillants, gares, lignes, siae_structures, logement, zones_attraction, siae_postes)

### Run Single Pipeline (V2 Version)

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  "https://odace-pipeline-588398598428.europe-west1.run.app/api/silver/geo?force=true"
```

**Expected**: 
- Pipeline runs successfully
- Creates `dim_commune` table in `silver_v2/` directory
- Returns job ID and status

### Run Full Pipeline (Bronze → Silver V2)

```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"force": true}' \
  https://odace-pipeline-588398598428.europe-west1.run.app/api/pipeline/run
```

**Expected**:
- 7 bronze pipelines run
- 8 silver v2 pipelines run
- Total: 15 pipelines
- All tables created in `silver_v2/` directory

### Check Documentation (Fixed)

Visit: https://odace-pipeline-588398598428.europe-west1.run.app/

Click "Doc" tab - should load DATA_MODEL.md successfully (404 error fixed)

### Monitor Job

```bash
# Get job_id from pipeline response, then:
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://odace-pipeline-588398598428.europe-west1.run.app/api/jobs/JOB_ID
```

## 3. Verify Data

### Check GCS for Silver V2 Tables

```bash
gsutil ls gs://icc-project-472009-data/silver_v2/
```

**Expected directories**:
- `dim_commune/` (from geo pipeline)
- `dim_accueillant/` (from accueillants pipeline)
- `dim_gare/` (from gares pipeline)
- `dim_ligne/` (from lignes pipeline)
- `dim_siae_structure/` (from siae_structures pipeline)
- `fact_logement/` (from logement pipeline)
- `fact_zone_attraction/` (from zones_attraction pipeline)
- `fact_siae_poste/` (from siae_postes pipeline)

### Inspect Table Schema

```bash
# Download a sample to verify schema
gsutil cat gs://icc-project-472009-data/silver_v2/dim_commune/_delta_log/00000000000000000000.json | head -50
```

**Expected columns**:
- `commune_sk` (surrogate key)
- `commune_code`, `commune_label`, `departement_code`, `region_code`
- `job_insert_id`, `job_insert_date_utc`, `job_modify_id`, `job_modify_date_utc` (metadata)

## 4. Verify Pipeline Names

The pipeline names remain unchanged for backward compatibility:

| API Name | V2 Table Name | Type |
|----------|---------------|------|
| `geo` | `dim_commune` | Dimension |
| `accueillants` | `dim_accueillant` | Dimension |
| `gares` | `dim_gare` | Dimension |
| `lignes` | `dim_ligne` | Dimension |
| `siae_structures` | `dim_siae_structure` | Dimension |
| `logement` | `fact_logement` | Fact |
| `zones_attraction` | `fact_zone_attraction` | Fact |
| `siae_postes` | `fact_siae_poste` | Fact |

## Troubleshooting

### Doc Tab Shows 404

**Solution**: 
- Check Cloud Run logs: `gcloud logs read --project=icc-project-472009 --limit=50`
- Look for "Looking for DATA_MODEL.md" messages
- File should be at `/app/DATA_MODEL.md` in container

### Wrong Number of Pipelines

**Expected**: 8 silver pipelines (V2)

If you see different counts:
- Check startup logs for "Registered X silver pipelines (V2 schema)"
- Verify silver_v2 imports in `app/main.py`
- Ensure NO old silver v1 imports

### Pipeline Not Found Error

**Cause**: Pipeline name typo or not imported

**Solution**:
- Use exact names: geo, accueillants, gares, lignes, siae_structures, logement, zones_attraction, siae_postes
- Check `/api/pipeline/list?layer=silver` for available names

### Data in Wrong Location

**Expected location**: `gs://bucket/silver_v2/`
**Old location**: `gs://bucket/silver/` (no longer written to)

If data appears in `silver/`:
- Old v1 pipeline is running (deployment issue)
- Redeploy with updated code

### Pipeline Execution Fails

**Check job details**:
```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://odace-pipeline-588398598428.europe-west1.run.app/api/jobs/JOB_ID
```

**Common issues**:
- Bronze data missing → Run bronze first
- GCS permissions → Check service account
- Memory issues → Increase Cloud Run memory limits
- Dependency errors → Check pipeline dependencies in list output

## Success Checklist

- [ ] Deploy completes without errors
- [ ] Documentation tab loads (no 404)
- [ ] `/api/pipeline/list?layer=silver` returns 8 pipelines
- [ ] Can run individual pipeline (e.g., `/api/silver/geo`)
- [ ] Full pipeline completes successfully
- [ ] 8 Delta tables created in `silver_v2/` directory
- [ ] Tables have surrogate keys (`_sk` columns)
- [ ] Tables have 4 metadata columns
- [ ] All job statuses show "success"

## API Reference

All endpoints work exactly as before:

```bash
# List pipelines
GET /api/pipeline/list?layer=silver

# Run individual pipeline
POST /api/silver/{pipeline_name}?force=true

# Run full pipeline
POST /api/pipeline/run
Body: {"bronze_only": false, "silver_only": false, "force": true}

# Check job status
GET /api/jobs/{job_id}

# Get job history
GET /api/jobs?limit=10
```

All require: `Authorization: Bearer YOUR_API_KEY`

## Next Steps After Validation

1. ✅ Verify all pipelines run successfully
2. ✅ Check data quality in silver_v2 tables
3. ⏳ Update applications to read from `silver_v2/` instead of `silver/`
4. ⏳ Update user documentation
5. ⏳ Monitor for 1-2 weeks
6. ⏳ Archive old `silver/` directory

---

**Remember**: The API is backward compatible. Only the internal implementation and data location changed.

