-- 🔧 EXERCICE E4 : ce schéma date de la première problématique.
-- L'adapter au schéma cible décrit dans docs/03_architecture.md
-- (fact_energie, fact_climat, fact_segment_bien, valeur_verte, score_territoire).

-- Homepedia : couche de service PostgreSQL / PostGIS
-- Exécuté automatiquement au premier démarrage du conteneur postgres.

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;   -- recherche floue sur les noms de communes

-- =========================================================
-- Référentiel géographique
-- =========================================================
CREATE TABLE IF NOT EXISTS ref_region (
    code_reg     CHAR(2) PRIMARY KEY,
    nom          TEXT NOT NULL,
    geom         geometry(MultiPolygon, 4326),
    geom_simple  geometry(MultiPolygon, 4326)
);

CREATE TABLE IF NOT EXISTS ref_departement (
    code_dep     VARCHAR(3) PRIMARY KEY,
    code_reg     CHAR(2) NOT NULL REFERENCES ref_region(code_reg),
    nom          TEXT NOT NULL,
    geom         geometry(MultiPolygon, 4326),
    geom_simple  geometry(MultiPolygon, 4326)
);

CREATE TABLE IF NOT EXISTS ref_commune (
    code_insee   CHAR(5) PRIMARY KEY,
    code_dep     VARCHAR(3) NOT NULL REFERENCES ref_departement(code_dep),
    nom          TEXT NOT NULL,
    population   INTEGER,
    codes_postaux TEXT[],
    geom         geometry(MultiPolygon, 4326),
    geom_simple  geometry(MultiPolygon, 4326),
    centroid     geometry(Point, 4326)
);
CREATE INDEX IF NOT EXISTS idx_commune_dep        ON ref_commune (code_dep);
CREATE INDEX IF NOT EXISTS idx_commune_geom       ON ref_commune USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_commune_centroid   ON ref_commune USING GIST (centroid);
CREATE INDEX IF NOT EXISTS idx_commune_nom_trgm   ON ref_commune USING GIN (nom gin_trgm_ops);

-- Table de passage COG (anciens codes -> code en vigueur)
CREATE TABLE IF NOT EXISTS ref_passage_cog (
    code_ancien  CHAR(5) PRIMARY KEY,
    code_actuel  CHAR(5) NOT NULL REFERENCES ref_commune(code_insee)
);

-- =========================================================
-- Faits (maille commune)
-- =========================================================
CREATE TABLE IF NOT EXISTS fact_marche (
    code_insee       CHAR(5)  NOT NULL REFERENCES ref_commune(code_insee),
    annee            SMALLINT NOT NULL,
    type_local       TEXT     NOT NULL CHECK (type_local IN ('Maison', 'Appartement', 'Tous')),
    nb_ventes        INTEGER  NOT NULL,
    prix_m2_median   NUMERIC(10,2),
    prix_m2_q1       NUMERIC(10,2),
    prix_m2_q3       NUMERIC(10,2),
    surface_mediane  NUMERIC(8,2),
    valeur_mediane   NUMERIC(12,2),
    PRIMARY KEY (code_insee, annee, type_local)
);
CREATE INDEX IF NOT EXISTS idx_marche_annee ON fact_marche (annee, type_local);

CREATE TABLE IF NOT EXISTS fact_loyer (
    code_insee      CHAR(5)  NOT NULL REFERENCES ref_commune(code_insee),
    annee           SMALLINT NOT NULL,
    type_bien       TEXT     NOT NULL,          -- appartement, maison, appartement_1_2p...
    loyer_m2        NUMERIC(8,2),
    loyer_m2_bas    NUMERIC(8,2),                -- intervalle de prédiction
    loyer_m2_haut   NUMERIC(8,2),
    nb_observations INTEGER,
    PRIMARY KEY (code_insee, annee, type_bien)
);

CREATE TABLE IF NOT EXISTS fact_socio_eco (
    code_insee          CHAR(5)  NOT NULL REFERENCES ref_commune(code_insee),
    annee               SMALLINT NOT NULL,
    population          INTEGER,
    revenu_median       NUMERIC(10,2),
    taux_pauvrete       NUMERIC(5,2),
    taux_chomage        NUMERIC(5,2),
    part_proprietaires  NUMERIC(5,2),
    part_res_secondaires NUMERIC(5,2),
    part_logements_vacants NUMERIC(5,2),
    logements_autorises INTEGER,
    PRIMARY KEY (code_insee, annee)
);

CREATE TABLE IF NOT EXISTS fact_equipement (
    code_insee  CHAR(5) NOT NULL REFERENCES ref_commune(code_insee),
    annee       SMALLINT NOT NULL,
    domaine     TEXT NOT NULL,                   -- commerces, santé, enseignement, sport...
    nb          INTEGER NOT NULL,
    PRIMARY KEY (code_insee, annee, domaine)
);

CREATE TABLE IF NOT EXISTS fact_concurrence (
    code_insee        CHAR(5) PRIMARY KEY REFERENCES ref_commune(code_insee),
    nb_agences        INTEGER NOT NULL,
    creations_3ans    INTEGER,
    ventes_par_agence NUMERIC(10,2)
);

CREATE TABLE IF NOT EXISTS fact_risque (
    code_insee      CHAR(5) PRIMARY KEY REFERENCES ref_commune(code_insee),
    nb_catnat_10ans INTEGER,
    risques         TEXT[],                      -- ex: {inondation, argiles}
    part_dpe_fg     NUMERIC(5,2),
    nb_dpe          INTEGER
);

CREATE TABLE IF NOT EXISTS fact_securite (
    code_insee   CHAR(5)  NOT NULL REFERENCES ref_commune(code_insee),
    annee        SMALLINT NOT NULL,
    indicateur   TEXT     NOT NULL,
    taux_pour_mille NUMERIC(8,3),
    PRIMARY KEY (code_insee, annee, indicateur)
);

CREATE TABLE IF NOT EXISTS fact_gare (
    code_uic     TEXT PRIMARY KEY,
    code_insee   CHAR(5) REFERENCES ref_commune(code_insee),
    nom          TEXT,
    voyageurs    BIGINT,
    geom         geometry(Point, 4326)
);
CREATE INDEX IF NOT EXISTS idx_gare_geom ON fact_gare USING GIST (geom);

CREATE TABLE IF NOT EXISTS fact_avis_synthese (
    code_insee      CHAR(5) PRIMARY KEY REFERENCES ref_commune(code_insee),
    nb_avis         INTEGER,
    sentiment_moyen NUMERIC(4,3),                -- -1 à 1
    top_themes      TEXT[],
    maj_le          TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS dim_cluster (
    code_insee  CHAR(5) PRIMARY KEY REFERENCES ref_commune(code_insee),
    cluster_id  SMALLINT NOT NULL,
    libelle     TEXT
);

-- =========================================================
-- Indicateurs en format long (multi-niveaux) et scores
-- =========================================================
CREATE TABLE IF NOT EXISTS indicateur_territoire (
    niveau      TEXT     NOT NULL CHECK (niveau IN ('commune', 'departement', 'region', 'france')),
    code        VARCHAR(5) NOT NULL,
    annee       SMALLINT NOT NULL,
    indicateur  TEXT     NOT NULL,
    valeur      DOUBLE PRECISION,
    PRIMARY KEY (niveau, code, annee, indicateur)
);
CREATE INDEX IF NOT EXISTS idx_indic_lookup ON indicateur_territoire (indicateur, niveau, annee);

CREATE TABLE IF NOT EXISTS score_opportunite (
    niveau        TEXT NOT NULL,
    code          VARCHAR(5) NOT NULL,
    profil        TEXT NOT NULL,
    score         NUMERIC(5,2),
    s_marche      NUMERIC(5,2),
    s_rentabilite NUMERIC(5,2),
    s_demande     NUMERIC(5,2),
    s_concurrence NUMERIC(5,2),
    s_cadre_de_vie NUMERIC(5,2),
    s_risques     NUMERIC(5,2),
    rang          INTEGER,
    PRIMARY KEY (niveau, code, profil)
);
CREATE INDEX IF NOT EXISTS idx_score_rang ON score_opportunite (niveau, profil, rang);

-- =========================================================
-- Vues matérialisées (agrégats départementaux / régionaux)
-- =========================================================
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_marche_departement AS
SELECT c.code_dep,
       m.annee,
       m.type_local,
       SUM(m.nb_ventes)                                              AS nb_ventes,
       -- médiane pondérée approximée par la moyenne pondérée des médianes communales
       SUM(m.prix_m2_median * m.nb_ventes) / NULLIF(SUM(m.nb_ventes), 0) AS prix_m2_moyen_pondere
FROM fact_marche m
JOIN ref_commune c USING (code_insee)
GROUP BY c.code_dep, m.annee, m.type_local
WITH NO DATA;
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_marche_dep ON mv_marche_departement (code_dep, annee, type_local);

CREATE MATERIALIZED VIEW IF NOT EXISTS mv_marche_region AS
SELECT d.code_reg,
       m.annee,
       m.type_local,
       SUM(m.nb_ventes) AS nb_ventes,
       SUM(m.prix_m2_median * m.nb_ventes) / NULLIF(SUM(m.nb_ventes), 0) AS prix_m2_moyen_pondere
FROM fact_marche m
JOIN ref_commune c USING (code_insee)
JOIN ref_departement d USING (code_dep)
GROUP BY d.code_reg, m.annee, m.type_local
WITH NO DATA;
CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_marche_reg ON mv_marche_region (code_reg, annee, type_local);

-- À lancer après chaque chargement :
--   REFRESH MATERIALIZED VIEW CONCURRENTLY mv_marche_departement;
--   REFRESH MATERIALIZED VIEW CONCURRENTLY mv_marche_region;
-- Remarque : la vraie médiane départementale est calculée dans Spark/dbt
-- (indicateur_territoire) ; ces vues servent d'accélérateur pour l'app.
