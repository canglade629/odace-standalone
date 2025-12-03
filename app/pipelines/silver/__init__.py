"""Silver layer pipelines - Cleaned and standardized dimension and fact tables.

This module contains pipelines for the silver layer which implements:
- Proper naming conventions (dim_* for dimensions, fact_* for facts)
- Surrogate keys (_sk) on all tables
- Metadata columns (job_insert_id, job_insert_date_utc, job_modify_id, job_modify_date_utc)
- Normalized schema with proper foreign key relationships
- SQL-based transformations via DuckDB for maintainability
"""
