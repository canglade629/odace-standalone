# Silver V1 → V2 Table Mapping

Quick reference for the migration from the old `silver` schema to the new `silver_v2` schema.

---

## Table Name Changes

| Old (silver) | New (silver_v2) | Type | Rows |
|-------------|-----------------|------|------|
| `geo` | `dim_commune` | Dimension | 34,935 |
| `accueillants` | `dim_accueillant` | Dimension | 1,293 |
| `gares` | `dim_gare` | Dimension | 2,974 |
| `lignes` | `dim_ligne` | Dimension | 933 |
| `siae_structures` | `dim_siae_structure` | Dimension | 40 |
| `logement` | `fact_logement` | Fact | 34,915 |
| `zones_attraction` | `fact_zone_attraction` | Fact | 26,209 |
| `siae_postes` | `fact_siae_poste` | Fact | 99 |

---

## Column Mappings by Table

### 1. geo → dim_commune

| Old Column | New Column | Change Type |
|-----------|-----------|-------------|
| *n/a* | `commune_sk` | **NEW** - Surrogate key (MD5 hash) |
| `CODGEO` | `commune_code` | Renamed |
| `LIBGEO` | `commune_label` | Renamed |
| `DEP` | `departement_code` | Renamed |
| *n/a* | `region_code` | **NEW** - Derived from departement |
| *n/a* | `job_insert_id` | **NEW** - Metadata |
| *n/a* | `job_insert_date_utc` | **NEW** - Metadata |
| *n/a* | `job_modify_id` | **NEW** - Metadata |
| *n/a* | `job_modify_date_utc` | **NEW** - Metadata |

### 2. accueillants → dim_accueillant

| Old Column | New Column | Change Type |
|-----------|-----------|-------------|
| *n/a* | `accueillant_sk` | **NEW** - Surrogate key |
| *n/a* | `commune_sk` | **NEW** - FK to dim_commune |
| `statut` | `statut` | Unchanged |
| `Ville` | `ville` | Trimmed |
| `Code_postal` | `code_postal` | Trimmed |
| `Latitude` | `latitude` | Cast to DOUBLE |
| `Longitude` | `longitude` | Cast to DOUBLE |
| *n/a* | `job_*` | **NEW** - Metadata (4 columns) |

**Note:** Deduplicated from 1,634 → 1,293 rows

### 3. gares → dim_gare

| Old Column | New Column | Change Type |
|-----------|-----------|-------------|
| *n/a* | `gare_sk` | **NEW** - Surrogate key |
| *n/a* | `commune_sk` | **NEW** - FK to dim_commune |
| `code_uic` | `code_uic` | Unchanged |
| `libelle` | `libelle` | Unchanged |
| `fret` | `fret` | **'O' → TRUE** (boolean) |
| `voyageurs` | `voyageurs` | **'O' → TRUE** (boolean) |
| `departemen` | `departement` | Renamed |
| `x_wgs84` | `longitude` | Renamed |
| `y_wgs84` | `latitude` | Renamed |
| *(all other geo columns)* | *(preserved)* | Unchanged |
| *n/a* | `job_*` | **NEW** - Metadata (4 columns) |

### 4. lignes → dim_ligne

| Old Column | New Column | Change Type |
|-----------|-----------|-------------|
| *n/a* | `ligne_sk` | **NEW** - Surrogate key |
| `code_ligne` | `ligne_code` | Renamed |
| `lib_ligne` | `libelle` | Renamed |
| `catlig` | `categorie` | Renamed |
| *n/a* | `is_tgv` | **NEW** - Derived boolean |
| `pkd` | `point_kilometrique_debut` | Renamed |
| `pkf` | `point_kilometrique_fin` | Renamed |
| `x_d_wgs84` | `longitude_debut` | Renamed |
| `y_d_wgs84` | `latitude_debut` | Renamed |
| `x_f_wgs84` | `longitude_fin` | Renamed |
| `y_f_wgs84` | `latitude_fin` | Renamed |
| *n/a* | `job_*` | **NEW** - Metadata (4 columns) |

### 5. siae_structures → dim_siae_structure

| Old Column | New Column | Change Type |
|-----------|-----------|-------------|
| *n/a* | `siae_structure_sk` | **NEW** - Surrogate key |
| *n/a* | `commune_sk` | **NEW** - FK to dim_commune |
| `id` | `id` | Unchanged |
| `siret` | `siret` | Validated (14 digits) |
| `type` | `structure_type` | Renamed |
| `bloque_candidatures` | `accepte_candidatures` | **INVERTED** boolean |
| `cree_le` | `date_creation` | Renamed |
| `mis_a_jour_le` | `date_mise_a_jour` | Renamed |
| `addresse_ligne_1` | `adresse_ligne1` | Renamed + typo fix |
| `addresse_ligne_2` | `adresse_ligne2` | Renamed + typo fix |
| *n/a* | `geo_insee_code` | **NEW** - From fuzzy matching |
| *n/a* | `ville_standardisee` | **NEW** - Standardized city name |
| *n/a* | `job_*` | **NEW** - Metadata (4 columns) |

### 6. logement → fact_logement

| Old Column | New Column | Change Type |
|-----------|-----------|-------------|
| *n/a* | `logement_sk` | **NEW** - Surrogate key |
| *n/a* | `commune_sk` | **NEW** - FK to dim_commune |
| `EPCI` | `epci_code` | Renamed |
| `loypredm2` | `loyer_predicted_m2` | Renamed |
| `lwr.IPm2` | `loyer_lower_bound_m2` | Renamed |
| `upr.IPm2` | `loyer_upper_bound_m2` | Renamed |
| `TYPPRED` | `prediction_level` | Renamed |
| `INSEE_C` | ~~(removed)~~ | **REMOVED** - Use commune_sk FK |
| `lib_commune` | ~~(removed)~~ | **REMOVED** - Denormalized |
| `lib_epci` | ~~(removed)~~ | **REMOVED** - Denormalized |
| `lib_departement` | ~~(removed)~~ | **REMOVED** - Denormalized |
| `lib_region` | ~~(removed)~~ | **REMOVED** - Denormalized |
| `DEP` | `code_departement` | Derived from commune_code |
| `REG` | `code_region` | Kept as code only |
| *n/a* | `job_*` | **NEW** - Metadata (4 columns) |

**Major Change:** Fully normalized - removed all `lib_*` columns

### 7. zones_attraction → fact_zone_attraction

| Old Column | New Column | Change Type |
|-----------|-----------|-------------|
| *n/a* | `zone_attraction_sk` | **NEW** - Surrogate key |
| *n/a* | `commune_sk` | **NEW** - FK to dim_commune (for CODGEO) |
| *n/a* | `commune_pole_sk` | **NEW** - FK to dim_commune (for pole) |
| `AAV2020` | `aire_attraction_code` | Renamed |
| `LIBAAV2020` | `aire_attraction_label` | Renamed |
| `CATEAAV2020` | `aire_attraction_categorie` | Renamed |
| `CODGEO` | ~~(removed)~~ | **REMOVED** - Use commune_sk FK |
| `CODGEOAAV` | ~~(removed)~~ | **REMOVED** - Use commune_pole_sk FK |
| `DEP` | `departement_code` | Renamed |
| `REG` | `region_code` | Renamed |
| *n/a* | `job_*` | **NEW** - Metadata (4 columns) |

**Major Change:** Dual foreign keys for commune and pole

### 8. siae_postes → fact_siae_poste

| Old Column | New Column | Change Type |
|-----------|-----------|-------------|
| *n/a* | `siae_poste_sk` | **NEW** - Surrogate key |
| *n/a* | `siae_structure_sk` | **NEW** - FK to dim_siae_structure |
| `id` | `poste_id` | Renamed |
| `rome` | `rome_code` | **EXTRACTED** from "(CODE)" |
| `appellation_modifiee` | `intitule_poste` | Renamed |
| `description` | `description_poste` | Renamed |
| `type_contrat` | `contrat_type` | Renamed |
| `recrutement_ouvert` | `poste_disponible` | Renamed + boolean |
| `nombre_postes_ouverts` | `postes_nombre` | Renamed |
| `cree_le` | `creation_date_utc` | Renamed |
| `mis_a_jour_le` | `modification_date_utc` | Renamed |
| *n/a* | `job_*` | **NEW** - Metadata (4 columns) |

**Major Change:** ROME code extraction using regex

---

## Key Transformation Patterns

### 1. Surrogate Keys
All tables now have an `_sk` column using MD5 hash:
```sql
MD5(natural_key_column) AS table_sk
```

### 2. Geographic Enrichment
Most tables now have `commune_sk` foreign key:
```sql
LEFT JOIN silver_v2_dim_commune c 
  ON source.insee_code = c.commune_code
```

### 3. Metadata Columns
All tables have these 4 columns:
- `job_insert_id VARCHAR`
- `job_insert_date_utc TIMESTAMP`
- `job_modify_id VARCHAR`
- `job_modify_date_utc TIMESTAMP`

### 4. Denormalization Removal
Removed all `lib_*` (label) columns - use JOINs instead:
```sql
-- Old:
SELECT lib_commune FROM silver.logement

-- New:
SELECT c.commune_label 
FROM silver_v2.fact_logement f
JOIN silver_v2.dim_commune c ON f.commune_sk = c.commune_sk
```

---

## API Query Updates

### Old Query Pattern
```python
GET /preview/silver/logement
```

### New Query Pattern
```python
# Same endpoint, different layer
GET /preview/silver_v2/fact_logement

# Get related commune info via FK
GET /preview/silver_v2/dim_commune?code=75056
```

---

## Join Examples

### Example 1: Get logement with commune name
```sql
SELECT 
    l.loyer_predicted_m2,
    c.commune_label,
    c.departement_code
FROM silver_v2.fact_logement l
JOIN silver_v2.dim_commune c ON l.commune_sk = c.commune_sk
WHERE l.loyer_predicted_m2 > 20
```

### Example 2: Get SIAE with structure details
```sql
SELECT 
    p.intitule_poste,
    p.rome_code,
    s.raison_sociale,
    s.ville,
    c.commune_label
FROM silver_v2.fact_siae_poste p
JOIN silver_v2.dim_siae_structure s ON p.siae_structure_sk = s.siae_structure_sk
LEFT JOIN silver_v2.dim_commune c ON s.commune_sk = c.commune_sk
WHERE p.poste_disponible = TRUE
```

### Example 3: Get zone with both commune and pole names
```sql
SELECT 
    z.aire_attraction_label,
    c1.commune_label AS commune,
    c2.commune_label AS pole_commune
FROM silver_v2.fact_zone_attraction z
JOIN silver_v2.dim_commune c1 ON z.commune_sk = c1.commune_sk
JOIN silver_v2.dim_commune c2 ON z.commune_pole_sk = c2.commune_sk
```

---

## Migration Impact Summary

| Impact Area | Change | Notes |
|------------|--------|-------|
| **Table Names** | All renamed with `dim_`/`fact_` prefix | Clear dimensional model |
| **Column Names** | Standardized with `_code`, `_label`, `_sk` | Consistent naming |
| **Surrogate Keys** | Added to all tables | MD5-based, unique |
| **Foreign Keys** | Geographic enrichment everywhere | Better relationships |
| **Denormalization** | Removed from fact_logement | Proper 3NF |
| **Data Types** | Explicit casts + COALESCE | No NULLs |
| **Deduplication** | Applied to dim_accueillant | -341 duplicate rows |
| **Metadata** | 4 columns added to all tables | Audit trail |

---

## Data Volume Changes

```
Total V1: 106,480 rows
Total V2: 101,398 rows
Difference: -5,082 rows (-4.8%)
```

**Reasons for reduction:**
- Deduplication in `dim_accueillant`: -341 rows
- Filtering invalid data (coordinates, codes): ~-4,741 rows

This is **expected and desired** - we're removing bad/duplicate data.

