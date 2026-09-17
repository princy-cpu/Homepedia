-- 🔧 EXERCICE E6 : modèle de la première problématique (loyers / concurrence).
-- À transformer en gold_score_territoire.sql (axes potentiel et risque_2040 + quadrant).

-- Score d'opportunité : sous-scores = rang percentile (0-100) au sein d'un même niveau.
-- Version initiale basée sur les indicateurs déjà disponibles ; les sous-scores
-- sans données valent 50 (neutre) en attendant les sources correspondantes.
-- Les pondérations reprennent config/scoring.yaml (profil par défaut ici :
-- reseau_agences) ; l'app recombine ensuite avec les curseurs de l'utilisateur.

{% set annee_ref = var('annee_ref', 2024) %}

with base as (
    select
        niveau,
        code,
        max(case when indicateur = 'nb_ventes' then valeur end)          as nb_ventes,
        max(case when indicateur = 'evol_prix_m2_3ans' then valeur end)  as evol_prix_m2_3ans
    from {{ ref('gold_indicateur_territoire') }}
    where annee = {{ annee_ref }}
    group by 1, 2
),

scores as (
    select
        niveau,
        code,
        100 * (percent_rank() over (partition by niveau order by nb_ventes)
             + percent_rank() over (partition by niveau order by evol_prix_m2_3ans)) / 2 as s_marche,
        cast(50 as double) as s_rentabilite,   -- TODO : rendement_brut (loyers)
        cast(50 as double) as s_demande,       -- TODO : population, revenus, chômage
        cast(50 as double) as s_concurrence,   -- TODO : SIRENE 68.31Z
        cast(50 as double) as s_cadre_de_vie,  -- TODO : BPE, gares, avis
        cast(50 as double) as s_risques        -- TODO : Géorisques, DPE
    from base
),

profil as (
    select
        niveau,
        code,
        'reseau_agences' as profil,
        0.30 * s_marche + 0.05 * s_rentabilite + 0.25 * s_demande
          + 0.25 * s_concurrence + 0.10 * s_cadre_de_vie + 0.05 * s_risques as score,
        s_marche, s_rentabilite, s_demande, s_concurrence, s_cadre_de_vie, s_risques
    from scores
)

select
    niveau,
    code,
    profil,
    cast(round(score, 2) as decimal(5, 2)) as score,
    cast(round(s_marche, 2) as decimal(5, 2))       as s_marche,
    cast(round(s_rentabilite, 2) as decimal(5, 2))  as s_rentabilite,
    cast(round(s_demande, 2) as decimal(5, 2))      as s_demande,
    cast(round(s_concurrence, 2) as decimal(5, 2))  as s_concurrence,
    cast(round(s_cadre_de_vie, 2) as decimal(5, 2)) as s_cadre_de_vie,
    cast(round(s_risques, 2) as decimal(5, 2))      as s_risques,
    cast(rank() over (partition by niveau, profil order by score desc) as integer) as rang
from profil
