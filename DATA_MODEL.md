# Odace Data Model

## Overview

The Odace data platform follows a **medallion architecture** with three layers:

- **Bronze**: Raw data ingestion (files + APIs)
- **Silver**: Cleaned, standardized tables (8 tables)
- **Gold**: Business aggregations and metrics

This document describes the **Silver layer** schema.

---

## Silver Layer Tables

### Core Entities

| Table | Type | Purpose | Rows |
|-------|------|---------|------|
| `geo` | Dimension | French communes (geographic reference) | ~34,935 |
| `accueillants` | Dimension | Host organization locations | ~1,293 |
| `gares` | Dimension | Railway stations | ~2,974 |
| `lignes` | Dimension | Railway lines | ~933 |
| `siae_structures` | Dimension | Social inclusion employment structures | ~1,976 |
| `logement` | Fact | Housing prices by commune | ~34,915 |
| `zones_attraction` | Fact | Urban area influence zones | ~26,209 |
| `siae_postes` | Fact | Job openings in SIAE structures | ~4,219 |

**Total: 107,454 rows**

---

## Understanding Surrogate Keys

All tables use **surrogate keys** (`_sk` suffix) for unique identification and joins:

- **Format**: MD5 hash-based unique identifier
- **Purpose**: Stable, consistent record identity
- **Usage**: Use `_sk` columns for all joins between tables

### Standard Columns

Every table includes:

| Column | Type | Description |
|--------|------|-------------|
| `{entity}_sk` | STRING | Surrogate key (MD5 hash) |
| `job_insert_id` | STRING | Pipeline that created the record |
| `job_insert_date_utc` | TIMESTAMP | When record was created |
| `job_modify_id` | STRING | Pipeline that last modified |
| `job_modify_date_utc` | TIMESTAMP | When record was last modified |

---

## Table Schemas

### 1. geo (Geographic Reference)

**Purpose**: Master reference table for French communes.

| Column | Type | Description |
|--------|------|-------------|
| `commune_sk` | STRING | **Surrogate key** (PK) |
| `commune_code` | STRING | INSEE code (5 digits) |
| `commune_label` | STRING | Commune name |
| `departement_code` | STRING | Department code (2 digits) |
| `region_code` | STRING | Region code |

**Key Column**: `commune_sk` is referenced by most other tables for geographic joins.

---

### 2. accueillants (Host Locations)

**Purpose**: Locations of host structures/organizations.

| Column | Type | Description |
|--------|------|-------------|
| `accueillant_sk` | STRING | **Surrogate key** (PK) |
| `commune_sk` | STRING | **FK** → `geo.commune_sk` |
| `statut` | STRING | Status of host structure |
| `ville` | STRING | City name |
| `code_postal` | STRING | Postal code |
| `latitude` | DOUBLE | WGS84 latitude |
| `longitude` | DOUBLE | WGS84 longitude |

---

### 3. gares (Railway Stations)

**Purpose**: Train station locations and metadata.

| Column | Type | Description |
|--------|------|-------------|
| `gare_sk` | STRING | **Surrogate key** (PK) |
| `commune_sk` | STRING | **FK** → `geo.commune_sk` |
| `code_uic` | STRING | UIC station code |
| `libelle` | STRING | Station name |
| `fret` | BOOLEAN | Freight service available |
| `voyageurs` | BOOLEAN | Passenger service available |
| `code_ligne` | STRING | Railway line code |
| `commune` | STRING | Commune name |
| `departement` | STRING | Department code |
| `latitude` | DOUBLE | WGS84 latitude |
| `longitude` | DOUBLE | WGS84 longitude |

**Filter**: Only passenger stations (`voyageurs = TRUE`)

---

### 4. lignes (Railway Lines)

**Purpose**: Railway line segments and characteristics.

| Column | Type | Description |
|--------|------|-------------|
| `ligne_sk` | STRING | **Surrogate key** (PK) |
| `code_ligne` | STRING | Line code |
| `libelle` | STRING | Line name |
| `categorie` | STRING | Line category |
| `is_tgv` | BOOLEAN | High-speed line flag |
| `rg_troncon` | INTEGER | Section rank |
| `longitude_debut` | DOUBLE | Start longitude |
| `latitude_debut` | DOUBLE | Start latitude |
| `longitude_fin` | DOUBLE | End longitude |
| `latitude_fin` | DOUBLE | End latitude |

---

### 5. siae_structures (SIAE Organizations)

**Purpose**: Social inclusion employment structures.

| Column | Type | Description |
|--------|------|-------------|
| `siae_structure_sk` | STRING | **Surrogate key** (PK) |
| `commune_sk` | STRING | **FK** → `geo.commune_sk` |
| `id` | STRING | Original structure UUID |
| `siret` | STRING | SIRET business identifier |
| `structure_type` | STRING | Type (EI, AI, ETTI, etc.) |
| `raison_sociale` | STRING | Legal name |
| `enseigne` | STRING | Trade name |
| `telephone` | STRING | Phone number |
| `courriel` | STRING | Email address |
| `site_web` | STRING | Website URL |
| `accepte_candidatures` | BOOLEAN | Accepting applications |
| `adresse_ligne1` | STRING | Address line 1 |
| `code_postal` | STRING | Postal code |
| `ville` | STRING | City name |
| `departement` | STRING | Department code |

---

### 6. logement (Housing Prices)

**Purpose**: Predicted housing rent prices by commune.

| Column | Type | Description |
|--------|------|-------------|
| `logement_sk` | STRING | **Surrogate key** (PK) |
| `commune_sk` | STRING | **FK** → `geo.commune_sk` |
| `epci_code` | STRING | EPCI (intercommunal) code |
| `loyer_predicted_m2` | DECIMAL | Predicted rent per m² |
| `loyer_lower_bound_m2` | DECIMAL | Lower prediction bound |
| `loyer_upper_bound_m2` | DECIMAL | Upper prediction bound |
| `prediction_level` | STRING | Prediction quality level |
| `code_departement` | STRING | Department code |
| `code_region` | STRING | Region code |

---

### 7. zones_attraction (Urban Influence Zones)

**Purpose**: Urban areas of influence (AAV - Aire d'Attraction des Villes).

| Column | Type | Description |
|--------|------|-------------|
| `zone_attraction_sk` | STRING | **Surrogate key** (PK) |
| `commune_sk` | STRING | **FK** → `geo.commune_sk` (commune) |
| `commune_pole_sk` | STRING | **FK** → `geo.commune_sk` (urban center) |
| `aire_attraction_code` | STRING | Urban area code |
| `aire_attraction_label` | STRING | Urban area name |
| `aire_attraction_categorie` | STRING | Urban area category |
| `departement_code` | STRING | Department code |
| `region_code` | STRING | Region code |

**Special**: This table has **two** foreign keys to `geo`:
- `commune_sk`: The commune in the urban area
- `commune_pole_sk`: The central city of the urban area

---

### 8. siae_postes (SIAE Job Openings)

**Purpose**: Active job positions in SIAE structures.

| Column | Type | Description |
|--------|------|-------------|
| `siae_poste_sk` | STRING | **Surrogate key** (PK) |
| `siae_structure_sk` | STRING | **FK** → `siae_structures.siae_structure_sk` |
| `poste_id` | STRING | Original position ID |
| `structure_id` | STRING | Parent structure ID (UUID) |
| `rome_code` | STRING | ROME job classification |
| `intitule_poste` | STRING | Job title |
| `description_poste` | STRING | Job description |
| `contrat_type` | STRING | Contract type |
| `poste_disponible` | BOOLEAN | Position available |
| `postes_nombre` | INTEGER | Number of openings |

---

## Join Relationships

### Primary Join Pattern: Geographic Hub

Most tables connect through the **`geo`** table using `commune_sk`:

```
                    ┌─────────────┐
                    │     geo     │
                    │ (commune_sk)│
                    └──────┬──────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
  ┌──────────┐      ┌──────────┐    ┌──────────────┐
  │ logement │      │  gares   │    │    siae      │
  └──────────┘      └──────────┘    │  structures  │
                                     └──────┬───────┘
                                            │
                                            ▼
                                    ┌──────────────┐
                                    │    siae      │
                                    │   postes     │
                                    └──────────────┘
```

### Key Join Examples

#### 1. Housing Prices by Commune

```sql
SELECT 
    g.commune_label,
    g.departement_code,
    l.loyer_predicted_m2
FROM silver_geo g
JOIN silver_logement l ON l.commune_sk = g.commune_sk
WHERE g.departement_code = '75'
ORDER BY l.loyer_predicted_m2 DESC;
```

#### 2. SIAE Jobs with Structure Details

```sql
SELECT 
    s.raison_sociale,
    s.ville,
    p.intitule_poste,
    p.postes_nombre
FROM silver_siae_structures s
JOIN silver_siae_postes p ON p.siae_structure_sk = s.siae_structure_sk
WHERE s.accepte_candidatures = TRUE
  AND p.poste_disponible = TRUE;
```

#### 3. Train Stations by Commune

```sql
SELECT 
    g.commune_label,
    COUNT(ga.gare_sk) as nb_gares
FROM silver_geo g
LEFT JOIN silver_gares ga ON ga.commune_sk = g.commune_sk
GROUP BY g.commune_label
HAVING COUNT(ga.gare_sk) > 0
ORDER BY nb_gares DESC;
```

#### 4. SIAE in Urban Areas

```sql
SELECT 
    za.aire_attraction_label,
    COUNT(DISTINCT s.siae_structure_sk) as nb_structures,
    SUM(p.postes_nombre) as total_postes
FROM silver_zones_attraction za
JOIN silver_geo g ON za.commune_sk = g.commune_sk
JOIN silver_siae_structures s ON s.commune_sk = g.commune_sk
LEFT JOIN silver_siae_postes p ON p.siae_structure_sk = s.siae_structure_sk
GROUP BY za.aire_attraction_label
ORDER BY total_postes DESC;
```

---

## Common Query Patterns

### Find Communes with SIAE and Low Housing Costs

```sql
SELECT 
    g.commune_label,
    l.loyer_predicted_m2,
    COUNT(s.siae_structure_sk) as nb_siae
FROM silver_geo g
JOIN silver_logement l ON l.commune_sk = g.commune_sk
JOIN silver_siae_structures s ON s.commune_sk = g.commune_sk
WHERE l.loyer_predicted_m2 < 10.0
GROUP BY g.commune_label, l.loyer_predicted_m2
HAVING COUNT(s.siae_structure_sk) > 0
ORDER BY nb_siae DESC, l.loyer_predicted_m2 ASC;
```

### Transport Accessibility

```sql
SELECT 
    s.raison_sociale,
    s.ville,
    ga.libelle as gare_proche,
    ga.code_ligne
FROM silver_siae_structures s
JOIN silver_geo g ON s.commune_sk = g.commune_sk
LEFT JOIN silver_gares ga ON ga.commune_sk = g.commune_sk
WHERE ga.voyageurs = TRUE;
```

---

## Data Quality Notes

### Foreign Key Coverage

- **logement** → `geo`: 100% (INSEE codes are source data)
- **siae_structures** → `geo`: ~90% (enriched via fuzzy city matching)
- **gares** → `geo`: Currently being improved
- **zones_attraction** → `geo`: 100% (INSEE codes are source data)

### Deduplication

All tables are **deduplicated** in the Silver layer:
- Unique records per surrogate key
- Latest data kept for time-series sources
- Composite key deduplication where needed

---

## Quick Reference

### All Foreign Keys

| Table | Foreign Key | References |
|-------|-------------|------------|
| `accueillants` | `commune_sk` | `geo.commune_sk` |
| `gares` | `commune_sk` | `geo.commune_sk` |
| `siae_structures` | `commune_sk` | `geo.commune_sk` |
| `logement` | `commune_sk` | `geo.commune_sk` |
| `zones_attraction` | `commune_sk` | `geo.commune_sk` |
| `zones_attraction` | `commune_pole_sk` | `geo.commune_sk` |
| `siae_postes` | `siae_structure_sk` | `siae_structures.siae_structure_sk` |

### Naming Conventions

- **Surrogate keys**: `{entity}_sk` (MD5 hash)
- **Code fields**: `{entity}_code` (official codes like INSEE, UIC, ROME)
- **Label fields**: `{entity}_label` (human-readable names)
- **Dates**: `{field}_date_utc` (UTC timestamps)
- **Foreign keys**: Referenced entity's `_sk` column

---

## Summary

The Silver layer provides **8 clean, join-ready tables** with:

✅ **Surrogate keys** (`_sk`) for stable record identification  
✅ **Geographic enrichment** via `commune_sk` joins  
✅ **Full metadata tracking** (insert/modify timestamps)  
✅ **Consistent naming** across all tables  
✅ **Deduplicated data** ready for analysis

**Primary join key**: `commune_sk` connects most tables through the `geo` hub.

---

*Last updated: December 3, 2025*  
*Schema version: Silver V2*
