"""Silver V2 layer pipelines with updated modeling standards.

This module contains pipelines for the silver_v2 layer which implements:
- Proper naming conventions (dim_* for dimensions, fact_* for facts)
- Surrogate keys (_sk) on all tables
- Metadata columns (job_insert_id, job_insert_date_utc, job_modify_id, job_modify_date_utc)
- Normalized schema with proper foreign keys
- French for domain entities, English for operations/technical terms
"""

__version__ = "2.0.0"

