-- =====================================================================
-- Modèle en étoile — Analyse du marché de l'emploi Data en France
-- PostgreSQL 14+ (testé sur Supabase)
-- Chargement : \copy <table> from 'data/clean/<table>.csv' csv header
-- =====================================================================
create schema if not exists jobmarket;
set search_path to jobmarket;

-- ---------- Dimensions --------------------------------------------------
create table if not exists dim_date (
  date        date primary key,
  year        int  not null,
  month       int  not null,
  month_name  text not null,
  week        text not null,          -- ISO : 2026-S45
  weekday     text not null,
  is_weekend  boolean not null
);

create table if not exists dim_skill (
  skill        text primary key,
  skill_family text not null,
  n_offers     int  not null
);

-- ---------- Faits -------------------------------------------------------
create table if not exists fact_offers (
  offer_id             uuid primary key,
  title                text,
  job_family           text,
  company              text,
  company_type         text,
  sector               text,
  source               text,
  contract_type        text,
  remote_policy        text,
  city                 text,
  department           text,
  region               text,
  salary_min           numeric(9,0),
  salary_max           numeric(9,0),
  salary_mid           numeric(9,0),
  salary_format        text,
  tjm_max              numeric(6,0),
  seniority            text,
  min_years_experience numeric(4,1),
  n_must_have          int,
  n_nice_to_have       int,
  n_red_flags          int,
  n_skills_detected    int,
  match_score          int,
  score_hard_skills    int,
  score_experience     int,
  score_logistics      int,
  ai_should_apply      text,
  decision             text,
  reject_reason        text,
  collected_at         timestamptz,
  collected_date       date references dim_date(date),
  collected_week       text
);

create table if not exists bridge_offer_skill (
  offer_id    uuid references fact_offers(offer_id) on delete cascade,
  skill       text references dim_skill(skill),
  skill_family text,
  requirement text,                   -- Indispensable / Souhaité / Mentionné
  primary key (offer_id, skill)
);

create table if not exists fact_applications (
  application_id uuid primary key,
  offer_id       uuid,                -- peut être null (saisie manuelle)
  company        text,
  title          text,
  job_family     text,
  channel        text,
  status         text,
  status_label   text,
  cv_variant     text,
  match_score    int,
  created_at     timestamptz,
  applied_at     date,
  updated_at     timestamptz,
  last_email_at  timestamptz,
  city           text,
  department     text,
  region         text,
  is_applied     boolean,
  days_to_apply  int
);

create table if not exists fact_status_history (
  history_id              uuid primary key,
  application_id          uuid references fact_applications(application_id) on delete cascade,
  from_status             text,
  to_status               text,
  changed_at              timestamptz,
  days_in_previous_status numeric(8,2)
);

create table if not exists fact_recommendations (
  recommendation_id uuid primary key,
  offer_id          uuid,
  source            text,
  origin            text,              -- email / search
  title             text,
  job_family        text,
  company           text,
  city              text,
  department        text,
  region            text,
  quick_score       int,
  status            text,              -- new / analyzed / accepted / rejected / filtered
  reject_reason     text,
  flag_senior       boolean,
  received_at       timestamptz,
  decided_at        timestamptz,
  received_date     date references dim_date(date),
  hours_to_decision numeric(8,2)
);

create index if not exists ix_offers_family   on fact_offers(job_family);
create index if not exists ix_offers_region   on fact_offers(region);
create index if not exists ix_offers_date     on fact_offers(collected_date);
create index if not exists ix_bridge_skill    on bridge_offer_skill(skill);
create index if not exists ix_apps_status     on fact_applications(status);
create index if not exists ix_reco_date       on fact_recommendations(received_date);
