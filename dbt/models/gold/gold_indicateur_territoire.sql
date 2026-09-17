-- Indicateurs en format long, aux 3 niveaux (commune, département, région).
-- Point de départ : prix au m², volume de ventes et évolution sur 3 ans.
-- Ajouter ici les autres indicateurs (rendement, démographie...) au fil des sources.
-- Les médianes départementales/régionales sont recalculées sur les ventes
-- (et non moyennées depuis les communes).

with ventes as (
    select
        v.annee,
        v.prix_m2,
        v.code_insee,
        v.code_departement,
        c.code_region,
        c.population
    from {{ source('silver', 'dvf_mutations') }} v
    left join {{ source('silver', 'ref_commune') }} c on c.code_insee = v.code_insee
),

agg as (
    select 'commune' as niveau, code_insee as code, annee,
           approx_percentile(prix_m2, 0.5) as prix_m2_median, count(*) as nb_ventes
    from ventes group by 1, 2, 3
    union all
    select 'departement', code_departement, annee,
           approx_percentile(prix_m2, 0.5), count(*)
    from ventes group by 1, 2, 3
    union all
    select 'region', code_region, annee,
           approx_percentile(prix_m2, 0.5), count(*)
    from ventes where code_region is not null group by 1, 2, 3
),

avec_evolution as (
    select
        a.*,
        100.0 * (a.prix_m2_median / nullif(lag(a.prix_m2_median, 3) over (
            partition by a.niveau, a.code order by a.annee), 0) - 1) as evol_prix_m2_3ans
    from agg a
)

select niveau, code, cast(annee as smallint) as annee, indicateur, valeur
from avec_evolution
cross join unnest(
    array['prix_m2_median', 'nb_ventes', 'evol_prix_m2_3ans'],
    array[prix_m2_median, cast(nb_ventes as double), evol_prix_m2_3ans]
) as t(indicateur, valeur)
where valeur is not null
