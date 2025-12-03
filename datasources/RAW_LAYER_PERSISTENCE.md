# Raw Layer Data Persistence for API Pipelines

## Overview
All API-based bronze pipelines now automatically persist raw API responses to the GCS raw layer before processing them into Delta tables. This provides a complete audit trail and enables historical data reprocessing.

## Implementation

### Architecture
```
API Source → Raw Layer (JSON) → Bronze Layer (Delta) → Silver/Gold
              ↓
        gs://jaccueille/raw/api/{table_name}/
```

### Location Pattern
```
gs://jaccueille/raw/api/{table_name}/{table_name}_{timestamp}.json
```

### File Naming Convention
- **Pattern:** `{table_name}_{YYYYMMDD_HHMMSS}.json`
- **Examples:**
  - `gares_20251202_153045.json`
  - `lignes_20251202_153120.json`
  - `open_data_loyers_appartements_2023_20251202_154500.json`
  - `open_data_loyers_appartements_2018_20251202_154530.json`

### Directory Structure
```
gs://jaccueille/raw/api/
├── gares/
│   ├── gares_20251202_153045.json
│   ├── gares_20251203_093012.json
│   └── gares_20251204_120530.json
├── lignes/
│   ├── lignes_20251202_153120.json
│   ├── lignes_20251203_093045.json
│   └── lignes_20251204_120600.json
├── open_data_loyers_appartements_2023/
│   └── open_data_loyers_appartements_2023_20251202_154500.json
└── open_data_loyers_appartements_2018/
    └── open_data_loyers_appartements_2018_20251202_154530.json
```

## Data Format

### JSON Structure
Raw files contain the complete API response as a JSON array:
```json
[
  {
    "__id": 1,
    "CODE_UIC": 87281451,
    "LIBELLE": "Renescure",
    "FRET": false,
    "VOYAGEURS": true,
    "CODE_LIGNE": 295000,
    "COMMUNE": "RENESCURE",
    ...
  },
  {
    "__id": 2,
    ...
  }
]
```

### Characteristics
- **Format:** Pretty-printed JSON (indented)
- **Encoding:** UTF-8
- **Content:** Complete API response with all fields
- **Size:** Variable depending on dataset (typically 1-50 MB)

## Benefits

### 1. Data Lineage & Audit Trail
- Complete record of every API fetch
- Timestamp shows exactly when data was retrieved
- Ability to trace any data issues back to source

### 2. Disaster Recovery
- Raw data can be reprocessed if bronze tables are corrupted
- No need to refetch from external APIs
- Historical snapshots preserved

### 3. Compliance & Governance
- Immutable record of source data
- Meets data governance requirements
- Audit trail for regulatory compliance

### 4. Historical Analysis
- Compare data over time
- Track changes in source data
- Analyze API response evolution

### 5. Reprocessing Capability
- Fix bugs in transformation logic by reprocessing raw data
- Test new transformations on historical data
- No dependency on external API availability

## Storage Considerations

### Estimated Storage per Pipeline

| Pipeline | Records | Raw Size | Daily Storage | Monthly Storage |
|----------|---------|----------|---------------|-----------------|
| gares | ~3,884 | ~2 MB | 2 MB | ~60 MB |
| lignes | ~1,069 | ~1 MB | 1 MB | ~30 MB |
| loyers_2023 | ~35,000 | ~15 MB | 15 MB | ~450 MB |
| loyers_2018 | ~35,441 | ~15 MB | 15 MB | ~450 MB |

**Total:** ~33 MB per run, ~990 MB per month (if run daily)

### Storage Management

#### Retention Policy Recommendation
```yaml
Lifecycle Rule:
  - Age > 90 days: Move to Nearline storage (cost savings)
  - Age > 365 days: Move to Coldline storage
  - Age > 730 days: Delete (optional, based on compliance needs)
```

#### Cost Optimization
- GCS Standard Storage: ~$0.02/GB/month
- GCS Nearline: ~$0.01/GB/month  
- GCS Coldline: ~$0.004/GB/month

**Estimated Monthly Cost:**
- Month 1-3: ~$0.02 (Standard)
- Month 4-12: ~$0.10 (mixed Standard/Nearline)
- Year 1 total: < $2/year

## Implementation Details

### Code Flow
```python
# In BaseAPIBronzePipeline.read_source_file()

1. Fetch data from API
   records = asyncio.run(self.fetch_all_data())

2. Save raw data to GCS
   table_name = self.get_target_table()
   self.save_raw_data(records, table_name)
   
3. Convert to DataFrame and continue processing
   df = self.normalize_json_to_dataframe(records)
   return df
```

### save_raw_data() Method
Located in `app/pipelines/base_api.py`:
```python
def save_raw_data(self, records: List[Dict[str, Any]], table_name: str) -> str:
    # Generate timestamped filename
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    filename = f"{table_name}_{timestamp}.json"
    
    # Construct raw path
    raw_path = f"{self.settings.raw_path}/api/{table_name}/{filename}"
    
    # Convert to JSON and upload
    json_content = json.dumps(records, indent=2, ensure_ascii=False)
    self.gcs.upload_from_string(json_content, raw_path)
    
    return raw_path
```

## Affected Pipelines

All API-based bronze pipelines automatically benefit from this feature:

### Transport Pipelines
- ✅ `BronzeGaresPipeline` → `raw/api/gares/`
- ✅ `BronzeLignesPipeline` → `raw/api/lignes/`

### Open Data Pipelines
- ✅ `BronzeOpenDataPipeline` → `raw/api/open_data_{resource_name}/`
  - Rental prices 2023
  - Rental prices 2018

### SIAE Pipelines (if applicable)
- ✅ Any pipeline extending `BaseAPIBronzePipeline`

## Monitoring & Validation

### Verify Raw Data Saved
```bash
# List raw files for gares
gsutil ls gs://jaccueille/raw/api/gares/

# View file contents
gsutil cat gs://jaccueille/raw/api/gares/gares_20251202_153045.json | head

# Check file size
gsutil du -sh gs://jaccueille/raw/api/gares/
```

### Pipeline Logs
Look for log messages:
```
INFO: Saving raw data to gs://jaccueille/raw/api/gares/gares_20251202_153045.json
INFO: Saved 3884 records to gs://jaccueille/raw/api/gares/gares_20251202_153045.json
```

## Reprocessing from Raw Data

### Future Enhancement
While raw data is now persisted, the current pipelines always fetch fresh data from the API. A future enhancement could add:

```python
def read_from_raw(self, raw_file_path: str) -> pd.DataFrame:
    """Load and process data from a raw JSON file."""
    json_content = self.gcs.download_file(raw_file_path)
    records = json.loads(json_content)
    return self.normalize_json_to_dataframe(records)
```

This would enable:
- Reprocessing historical data without API calls
- Testing transformations on known datasets
- Recovery from bronze table corruption

## Best Practices

### 1. Regular Monitoring
- Check raw layer size monthly
- Verify files are being created
- Monitor for any upload failures

### 2. Lifecycle Policies
- Implement GCS lifecycle rules
- Archive old data to cheaper storage tiers
- Delete very old data per compliance requirements

### 3. Documentation
- Document what each raw file contains
- Keep metadata about source API versions
- Track any schema changes over time

### 4. Access Control
- Restrict write access to pipeline service accounts
- Provide read-only access for analysts
- Audit access logs periodically

## Summary

✅ **Implemented:** All API pipelines now save raw JSON to GCS  
✅ **Location:** `gs://jaccueille/raw/api/{table_name}/`  
✅ **Naming:** `{table_name}_{YYYYMMDD_HHMMSS}.json`  
✅ **Format:** Pretty-printed JSON  
✅ **Cost:** < $2/year with lifecycle policies  
✅ **Benefits:** Audit trail, disaster recovery, reprocessing capability  

This feature provides enterprise-grade data governance and reliability for all API-based data ingestion.

