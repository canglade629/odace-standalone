# SIAE Data Exploration Summary

## Bronze Layer Schema Analysis

Based on exploration of the SIAE API (`/siaes/` endpoint), we have identified the following:

### 1. SIAE Structures (bronze.siae_structures)

**18 columns at structure level:**
- `id` - UUID, primary key
- `siret` - Business identifier (14 digits)
- `type` - Structure type (EI, AI, ETTI, etc.)
- `raison_sociale` - Legal company name
- `enseigne` - Trade name
- `telephone` - Phone number
- `courriel` - Email address
- `site_web` - Website URL
- `description` - Text description
- `bloque_candidatures` - Boolean, whether accepting applications
- `cree_le` - Creation timestamp
- `mis_a_jour_le` - Update timestamp
- `addresse_ligne_1` - Address line 1
- `addresse_ligne_2` - Address line 2
- `code_postal` - Postal code (5 digits)
- `ville` - City name
- `departement` - Department code (2-3 characters)
- `postes` - Nested array of job positions

**Geographic Join Keys:**
- `code_postal` → Can map to geo data via postal code
- `ville` → Can match with commune names in bronze.geo
- `departement` → Department code

**Note:** The API does NOT provide INSEE codes directly, so joins with bronze.geo will need to be done via city name + postal code matching.

### 2. SIAE Postes (bronze.siae_postes) 

**Job positions extracted from structures.postes:**
- `structure_id` - Foreign key to structures
- `structure_siret` - SIRET reference
- `id` - Poste ID
- `rome` - ROME code (job classification)
- `cree_le` - Creation timestamp
- `mis_a_jour_le` - Update timestamp
- `recrutement_ouvert` - Whether actively recruiting
- `description` - Job description text
- `appellation_modifiee` - Modified job title
- `type_contrat` - Contract type
- `nombre_postes_ouverts` - Number of open positions
- `lieu` - Location (may be nested)
- `profil_recherche` - Sought profile

## Join Compatibility Analysis

### With bronze.geo (INSEE codes, commune names)
- ✅ **Join Method**: `ville` (city name) + potentially `code_postal`
- ⚠️ **Challenge**: No direct INSEE code in SIAE data
- **Solution**: Silver layer will standardize city names and map to INSEE codes

### With bronze.accueillants (host locations)
- ✅ **Join Method**: Similar structure with addresses and postal codes
- ✅ **Spatial Analysis**: Both have coordinates (accueillants has lat/long, SIAE has addresses)
- **Use Case**: Proximity analysis between host structures and employment opportunities

### With bronze.logement (housing data)
- ✅ **Join Method**: Via postal code or commune (after INSEE mapping)
- **Use Case**: Housing availability near SIAE employment locations

### With bronze.gares/lignes (transportation)
- ✅ **Join Method**: Via commune/INSEE codes (after mapping)
- **Use Case**: Public transport accessibility to SIAE locations

## Silver Layer Design

### silver.siae_structures

**Objectives:**
1. Standardize addresses
2. Map to INSEE codes by matching city names with bronze.geo
3. Remove nested postes (handled in separate table)
4. Clean and deduplicate by SIRET
5. Add geographic enrichment

**Proposed Schema:**
```sql
SELECT 
    id,
    siret,
    type as structure_type,
    raison_sociale as legal_name,
    enseigne as trade_name,
    COALESCE(telephone, '') as phone,
    COALESCE(courriel, '') as email,
    COALESCE(site_web, '') as website,
    description,
    bloque_candidatures as accepting_applications,
    CAST(cree_le AS TIMESTAMP) as created_at,
    CAST(mis_a_jour_le AS TIMESTAMP) as updated_at,
    addresse_ligne_1 as address_line_1,
    addresse_ligne_2 as address_line_2,
    code_postal as postal_code,
    UPPER(TRIM(ville)) as city,
    departement as department,
    -- Join with geo to get INSEE code
    g.code_insee as insee_code,
    g.nom_standard as standardized_city_name
FROM bronze_siae_structures s
LEFT JOIN bronze_geo g 
    ON UPPER(TRIM(s.ville)) = UPPER(TRIM(g.nom_standard))
    AND s.code_postal = g.code_postal  -- Additional match for precision
```

### silver.siae_postes

**Objectives:**
1. Link to structure
2. Clean job classification codes
3. Parse contract types
4. Standardize boolean fields

**Proposed Schema:**
```sql
SELECT 
    p.id as poste_id,
    p.structure_id,
    p.structure_siret,
    p.rome as rome_code,
    p.appellation_modifiee as job_title,
    p.description as job_description,
    p.type_contrat as contract_type,
    CAST(p.recrutement_ouvert AS BOOLEAN) as is_recruiting,
    COALESCE(p.nombre_postes_ouverts, 0) as positions_available,
    CAST(p.cree_le AS TIMESTAMP) as created_at,
    CAST(p.mis_a_jour_le AS TIMESTAMP) as updated_at,
    -- Link back to structure for geographic context
    s.city,
    s.postal_code,
    s.insee_code
FROM bronze_siae_postes p
LEFT JOIN silver_siae_structures s ON p.structure_id = s.id
```

## Data Volume Estimates

Based on sample (3 departments: 75, 69, 13):
- ~20 structures per page
- Average ~2-3 postes per structure
- France has 101 departments

**Estimated totals:**
- Structures: 5,000-10,000
- Postes: 10,000-30,000

## Implementation Plan

1. ✅ Bronze pipelines created (siae_structures, siae_postes)
2. ⏭️ Run bronze pipelines to fetch full data
3. ⏭️ Implement silver transformations with geo joins
4. ⏭️ Test and validate joins
5. ⏭️ Update documentation

