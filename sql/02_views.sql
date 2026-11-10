-- =====================================================================
-- Vues analytiques — réponses aux questions métier du dashboard
-- =====================================================================
set search_path to jobmarket;

-- Q1. Quelles compétences le marché demande-t-il, et à quel niveau d'exigence ?
create or replace view v_skill_demand as
select
  b.skill,
  b.skill_family,
  count(*)                                                   as n_offers,
  round(100.0 * count(*) / (select count(*) from fact_offers), 1) as pct_offers,
  count(*) filter (where b.requirement = 'Indispensable')    as n_must_have,
  round(100.0 * count(*) filter (where b.requirement = 'Indispensable') / count(*), 1) as pct_must_have
from bridge_offer_skill b
group by b.skill, b.skill_family
order by n_offers desc;

-- Q2. Salaires par famille de poste (uniquement les offres qui l'affichent)
create or replace view v_salary_by_family as
select
  job_family,
  count(*)                                     as n_offers,
  count(salary_mid)                            as n_with_salary,
  round(100.0 * count(salary_mid) / count(*),1) as pct_transparent,
  round(avg(salary_min))                       as avg_salary_min,
  round(avg(salary_max))                       as avg_salary_max,
  round(percentile_cont(0.5) within group (order by salary_mid)::numeric) as median_salary
from fact_offers
group by job_family
order by n_offers desc;

-- Q3. Répartition géographique et politique de télétravail
create or replace view v_geo_remote as
select
  region,
  count(*) as n_offers,
  round(100.0 * count(*) filter (where remote_policy = 'Hybride') / count(*), 1)             as pct_hybride,
  round(100.0 * count(*) filter (where remote_policy = 'Télétravail complet') / count(*), 1) as pct_full_remote,
  round(100.0 * count(*) filter (where remote_policy = 'Présentiel') / count(*), 1)          as pct_presentiel,
  round(100.0 * count(*) filter (where remote_policy = 'Non précisé') / count(*), 1)         as pct_non_precise
from fact_offers
group by region
order by n_offers desc;

-- Q4. Séniorité demandée : le « marché junior » existe-t-il ?
create or replace view v_seniority as
select
  job_family,
  seniority,
  count(*) as n_offers,
  round(100.0 * count(*) / sum(count(*)) over (partition by job_family), 1) as pct_in_family
from fact_offers
group by job_family, seniority
order by job_family, n_offers desc;

-- Q5. Entonnoir de candidature : du flux entrant à l'entretien
create or replace view v_funnel as
select 'Offres reçues (recommandations)' as stage, 1 as stage_order, count(*) as n from fact_recommendations
union all
select 'Retenues après tri rapide', 2, count(*) from fact_recommendations where status in ('accepted','analyzed')
union all
select 'Offres analysées en détail', 3, count(*) from fact_offers
union all
select 'Acceptées par l''IA + candidate', 4, count(*) from fact_offers where decision = 'accepted'
union all
select 'Candidatures envoyées', 5, count(*) from fact_applications where is_applied
union all
select 'Entretiens', 6, count(*) from fact_applications where status in ('entretien','accepte','offre')
order by stage_order;

-- Q6. Pourquoi les offres sont-elles écartées ?
create or replace view v_reject_reasons as
select reject_reason, count(*) as n,
       round(100.0 * count(*) / sum(count(*)) over (), 1) as pct
from fact_recommendations
where status = 'rejected' and reject_reason <> ''
group by reject_reason
order by n desc;

-- Q7. Quelle source d'offres est la plus rentable ? (taux de conversion par canal)
create or replace view v_source_quality as
select
  r.source,
  count(*)                                                     as n_received,
  count(*) filter (where r.status = 'accepted')                as n_accepted,
  round(100.0 * count(*) filter (where r.status = 'accepted') / count(*), 1) as acceptance_rate,
  round(100.0 * count(*) filter (where r.flag_senior) / count(*), 1)         as pct_too_senior,
  round(avg(r.quick_score), 1)                                 as avg_quick_score
from fact_recommendations r
group by r.source
order by n_received desc;

-- Q8. Délai moyen passé dans chaque statut (jours)
create or replace view v_status_durations as
select from_status, to_status, count(*) as n_transitions,
       round(avg(days_in_previous_status)::numeric, 1)    as avg_days,
       round(percentile_cont(0.5) within group (order by days_in_previous_status)::numeric, 1) as median_days
from fact_status_history
where from_status is not null
group by from_status, to_status
order by n_transitions desc;

-- Q9. Écart entre le score rapide (liste) et le score complet (analyse) — fiabilité du tri
create or replace view v_score_gap as
select
  r.recommendation_id, r.title, r.quick_score, o.match_score as full_score,
  o.match_score - r.quick_score as gap
from fact_recommendations r
join fact_offers o on o.offer_id = r.offer_id   -- lien posé par JobPilot à l'import
where r.quick_score is not null;
