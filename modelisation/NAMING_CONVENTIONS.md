# Conventions de Nommage – Data Modeling

> **Version**: 1.0  
> **Date**: 2025-12-01  
> **Contexte**: Architecture Medallion (Silver/Gold layers) – PostgreSQL

---

## Principes Généraux

### Règle Fondamentale : Séparation Entité / Opération

- **Entités du domaine** → **Français** (les "choses" que vous mesurez : loyer, commune, logement)
- **Tout le reste** → **Anglais** (attributs, opérations, transformations, technique)

### Structure de Nommage

```
[domain_entity]_[attribute]_[unit]_[technical_suffix]
```

**Exemples** :
- `loyer_predicted_m2` (entité: loyer, attribut: predicted, unité: m2)
- `count_observations_grid` (opération: count, cible: observations, contexte: grid)
- `commune_sk` (entité: commune, suffixe technique: SK)

---

## Langue par Type de Concept

### 🇫🇷 Français (Entités du Domaine UNIQUEMENT)

**Entités du domaine - les "choses" métier** :
- `loyer` (rent)
- `commune`, `epci`, `departement`, `region`, `pays` (geographic entities)
- `annee`, `trimestre`, `mois` (time periods - but consider English for consistency)
- `logement`, `batiment`, `proprietaire` (housing domain entities)
- `locataire`, `bailleur` (tenant, landlord)

> **Principe** : Si c'est une entité concrète de votre domaine métier, gardez-le en français.

### 🇬🇧 Anglais (Tout le Reste)

**Attributs et qualificatifs** :
- `predicted`, `observed`, `estimated`, `calculated`
- `lower`, `upper`, `average`, `median`
- `minimum`, `maximum`, `total`

**Opérations et agrégations** :
- `count`, `sum`, `avg`, `min`, `max`

**Concepts statistiques et techniques** :
- `grid`, `quality`, `bound`, `interval`
- `r2_adjusted`, `confidence`, `error`

**Concepts de stockage** :
- `_sk` (Surrogate Key)
- `_id` (Identifier)
- `_date_utc` (Date/timestamp fields)

**Métadonnées système** :
- `job_insert_id`, `job_insert_date_utc`
- `job_modify_id`, `job_modify_date_utc`

---

## Règles d'Écriture

### 1. Format des Noms

- ✅ **Tout en minuscules** : `loyer_predit_m2`
- ✅ **Séparateur** : underscore `_`
- ❌ Pas de CamelCase : ~~`loyerPredit`~~
- ❌ Pas de majuscules : ~~`LOYER_PREDIT`~~

### 2. Abréviations

**Interdites (sauf exceptions)** :
- ❌ `typpred` → ✅ `prediction_type`
- ❌ `lwr` → ✅ `lower` ou `lower_bound`
- ❌ `upr` → ✅ `upper` ou `upper_bound`
- ❌ `nbobs` → ✅ `count_observations`
- ❌ `nbr` → ✅ `count` (utiliser le terme SQL standard)
- ❌ `upd_date` → ✅ `update_date` ou `modify_date`

**Exceptions autorisées** :
- ✅ `m2` (mètre carré – universellement compris)
- ✅ `r2` (coefficient de détermination – standard statistique)
- ✅ `epci` (acronyme officiel)
- ✅ `insee` (acronyme officiel)
- ✅ `utc` (fuseau horaire)

### 3. Unités de Mesure

Toujours en suffixe, collées à l'attribut :
- `loyer_predicted_m2` (loyer prédit au mètre carré)
- `surface_total_m2` (surface totale en mètres carrés)
- `prix_average_euros` (si nécessaire de préciser la devise)

### 4. Préfixes et Suffixes Obligatoires

**Suffixes techniques (toujours en anglais)** :
- `_sk` : Surrogate Key (clé de substitution)
- `_code` : Code officiel (ex: code INSEE, code postal)
- `_label` : Libellé officiel (ex: nom de commune)
- `_date_utc` : Champs de type date/timestamp en UTC
- `_id` : Identifiant système

**Préfixes de table** :
- `dim_` : Tables de dimension
- `fact_` : Tables de faits

---

## Types de Colonnes

### Clés (Keys)

```sql
-- Clé de substitution (hash dbt ou serial)
loyer_commune_sk        STRING

-- Clés étrangères
commune_sk              STRING    -- FK to dim_commune
epci_sk                 STRING    -- FK to dim_epci
```

### Mesures (Facts)

```sql
-- Mesures principales
loyer_predicted_m2             DECIMAL(10,2)
loyer_observed_m2              DECIMAL(10,2)

-- Bornes d'intervalle
loyer_lower_bound_m2           DECIMAL(10,2)
loyer_upper_bound_m2           DECIMAL(10,2)

-- Compteurs
count_observations_grid        INTEGER
count_observations_commune     INTEGER
count_annonces                 INTEGER
```

### Indicateurs de Qualité

```sql
-- Métriques statistiques
quality_r2_adjusted            DECIMAL(5,4)    -- Entre 0 et 1
score_confidence               DECIMAL(5,4)
rate_completeness              DECIMAL(5,4)
```

### Métadonnées Obligatoires

**Chaque table doit contenir** :

```sql
job_insert_id           STRING          -- Job ayant inséré la ligne
job_insert_date_utc     TIMESTAMP_NTZ   -- Date d'insertion (UTC)
job_modify_id           STRING          -- Job ayant modifié la ligne
job_modify_date_utc     TIMESTAMP_NTZ   -- Date de modification (UTC)
```

---

## Entités MDM (Master Data Management)

Les entités suivantes sont gérées par le MDM : `commune`, `departement`, `region`, `pays`.

### Structure Standard

```sql
CREATE TABLE dim_<entite> (
    <entite>_sk      STRING,          -- Clé de substitution (hash dbt)
    <entite>_code    STRING,          -- Code officiel MDM
    <entite>_label   STRING,          -- Libellé officiel MDM
    
    -- Métadonnées obligatoires
    job_insert_id        STRING,
    job_insert_date_utc  TIMESTAMP_NTZ,
    job_modify_id        STRING,
    job_modify_date_utc  TIMESTAMP_NTZ,
    
    PRIMARY KEY (<entite>_sk)
);
```

**Exemple concret** :

```sql
CREATE TABLE dim_commune (
    commune_sk           STRING,
    commune_code         STRING,        -- Code INSEE
    commune_label        STRING,        -- Nom officiel
    
    job_insert_id        STRING,
    job_insert_date_utc  TIMESTAMP_NTZ,
    job_modify_id        STRING,
    job_modify_date_utc  TIMESTAMP_NTZ,
    
    PRIMARY KEY (commune_sk)
);
```

### Codes Géographiques

- **Région** : Code INSEE région (2 chiffres)
- **Département** : Code INSEE département (2 ou 3 chiffres)
- **Commune** : Code INSEE commune (5 chiffres)
- **Arrondissement** : Certains codes (ex: `75101` pour Paris 01) réfèrent à la commune parent (`75056`)

---

## Arbre de Décision pour le Nommage

Lorsque vous nommez une nouvelle colonne, posez-vous ces questions :

### 1️⃣ Est-ce un concept métier spécifique à votre domaine ?
→ **Français**  
Exemples : `loyer`, `commune`, `maille`, `predit`

### 2️⃣ Est-ce un concept technique/système transversal ?
→ **Anglais**  
Exemples : `_sk`, `_id`, `job_*`, `_date_utc`

### 3️⃣ Est-ce un terme statistique/mathématique universel ?
→ **Conserver l'original**  
Exemples : `r2` (pas `r_deux`), `m2` (pas `metre_carre`)

### 4️⃣ L'abréviation causerait-elle de la confusion ?
→ **Écrire en entier**  
Exemples : `nombre_observations` pas `nb_obs`

---

## Exemples Complets

### Table de Faits : Loyers Communaux

```sql
CREATE TABLE fact_loyer_commune (
    -- Clé primaire
    loyer_commune_sk                STRING,
    
    -- Clés étrangères (dimensions)
    commune_sk                      STRING,
    epci_sk                         STRING,
    annee_sk                        STRING,
    prediction_type_sk              STRING,
    
    -- Faits (mesures)
    loyer_predicted_m2              DECIMAL(10,2),
    loyer_lower_bound_m2            DECIMAL(10,2),
    loyer_upper_bound_m2            DECIMAL(10,2),
    
    -- Indicateurs de qualité
    quality_r2_adjusted             DECIMAL(5,4),
    count_observations_grid         INTEGER,
    count_observations_commune      INTEGER,
    
    -- Métadonnées obligatoires
    job_insert_id                   STRING,
    job_insert_date_utc             TIMESTAMP_NTZ,
    job_modify_id                   STRING,
    job_modify_date_utc             TIMESTAMP_NTZ,
    
    PRIMARY KEY (loyer_commune_sk),
    FOREIGN KEY (commune_sk) REFERENCES dim_commune(commune_sk),
    FOREIGN KEY (epci_sk) REFERENCES dim_epci(epci_sk),
    FOREIGN KEY (prediction_type_sk) REFERENCES dim_prediction_type(prediction_type_sk)
);

-- Commentaires (en français)
COMMENT ON TABLE fact_loyer_commune IS 
    'Table de faits contenant les loyers prédits par commune pour le 3ème trimestre 2018';

COMMENT ON COLUMN fact_loyer_commune.loyer_predicted_m2 IS 
    'Loyer prévu (charges comprises) au mètre carré, estimé à partir des annonces en ligne';

COMMENT ON COLUMN fact_loyer_commune.quality_r2_adjusted IS 
    'Coefficient de détermination ajusté (R² ajusté) mesurant la qualité du modèle prédictif';
```

### Table de Dimension : Types de Prédiction

```sql
CREATE TABLE dim_prediction_type (
    prediction_type_sk      STRING,
    prediction_type_code    STRING,
    prediction_type_label   STRING,
    
    job_insert_id           STRING,
    job_insert_date_utc     TIMESTAMP_NTZ,
    job_modify_id           STRING,
    job_modify_date_utc     TIMESTAMP_NTZ,
    
    PRIMARY KEY (prediction_type_sk)
);

COMMENT ON TABLE dim_prediction_type IS 
    'Type de maille statistique utilisée pour la prédiction du loyer (commune, EPCI, grille)';
```

---

## Checklist de Migration

Lors de la migration d'une table avec anciens noms :

- [ ] Créer un glossaire de mappage (ancien → nouveau)
- [ ] Documenter les termes français avec traductions anglaises dans les `COMMENT`
- [ ] Mettre à jour tous les modèles dbt référençant ces colonnes
- [ ] Ajouter les `COMMENT ON COLUMN` pour documentation
- [ ] Vérifier la cohérence avec les tables liées (FK)
- [ ] Créer les dimensions manquantes si nécessaire
- [ ] Valider avec les utilisateurs métier finaux

---

## Glossaire de Référence

| Concept | Français | Anglais | Dans les colonnes |
|---------|----------|---------|-------------------|
| **Entités du domaine** | | | |
| Loyer | loyer | rent | `loyer_predicted_m2` ✅ |
| Commune | commune | municipality | `commune_sk` ✅ |
| EPCI | epci | intercommunality | `epci_sk` ✅ |
| Logement | logement | housing | `logement_type_sk` ✅ |
| Propriétaire | proprietaire | owner | `proprietaire_sk` ✅ |
| **Opérations/Attributs** | | | |
| Prédit | prédit | predicted | `predicted` ✅ |
| Observé | observé | observed | `observed` ✅ |
| Inférieur | inférieur | lower | `lower_bound` ✅ |
| Supérieur | supérieur | upper | `upper_bound` ✅ |
| Maille | maille | grid | `grid` ✅ |
| Qualité | qualité | quality | `quality` ✅ |
| Nombre | nombre | count | `count` ✅ (pas `nbr`) |

---

## Références

- **Documentation interne** : `INSTRUCTIONS_MODELISATION.md`
- **Architecture** : Medallion (Bronze → Silver → Gold)
- **Base de données** : PostgreSQL
- **Outil de transformation** : dbt
- **Référentiels géographiques** : Codes INSEE (France)
