# Marché de l'emploi Data en France — étude à partir de 170 offres analysées

> Pipeline Python → modèle en étoile PostgreSQL → dashboard Power BI / Streamlit.
> Données : 172 offres d'emploi analysées en détail, 745 offres reçues et triées, 203 candidatures suivies, 381 changements de statut — collectées entre le 27 octobre et le 10 novembre 2026 via [JobPilot](https://jobpilot-ashy.vercel.app/), l'outil de suivi de candidatures que j'ai développé.

**Livrables :** rapport Power BI (`powerbi/`) · dashboard Tableau Public (`tableau/`, _lien à venir_) · version Python Streamlit (`app/`, _lien à venir_). Une seule source de données (`tableau/source_marche_emploi_data.xlsx`), trois outils.

---

## La question métier

Je cherche un poste de Data Analyst / BI en France. Plutôt que de candidater à l'aveugle, j'ai voulu répondre avec des données à cinq questions :

1. Quelles compétences le marché demande-t-il vraiment, et lesquelles sont *indispensables* plutôt que *souhaitées* ?
2. Combien paient les postes, et quelle part des offres affiche un salaire ?
3. Où sont les postes, et le télétravail est-il la norme ?
4. Le « marché junior » existe-t-il, ou les offres exigent-elles 3 à 5 ans d'expérience ?
5. Quelle source d'offres (LinkedIn, Indeed, HelloWork…) produit le moins de bruit ?

## Ce que disent les données

| # | Constat | Chiffre |
|---|---|---|
| 1 | **SQL est la compétence n° 1, loin devant Python.** Les compétences « métier » (Agile, gestion de projet, recueil de besoins) pèsent autant que les compétences techniques. | SQL cité dans **36 %** des offres, Agile/Scrum 28 %, Power BI 21 %, Python 20 %, Excel 19 % |
| 2 | **L'IA est entrée dans les fiches de poste Data.** Près d'une offre sur quatre mentionne IA / LLM / IA générative, y compris pour des postes Business Analyst. | **23 %** des offres |
| 3 | **La transparence salariale reste faible**, surtout chez les ESN. Quand il est affiché, le salaire médian est de 42,5 k€ ; les Data Engineers sont les mieux payés, les postes BI/PMO les moins. | **17 %** des offres affichent un salaire · médiane **42,5 k€** · Data Engineer 52,5 k€, Data Analyst 46 k€, Consultant BI 41 k€ |
| 4 | **Le marché junior est minoritaire.** Parmi les offres qui précisent la séniorité, 60 % demandent 3 à 5 ans ; un tiers seulement sont ouvertes à 0-2 ans. Côté flux entrant, « trop senior » est la première raison de rejet. | **32 %** d'offres juniors (séniorité connue) · **42 %** des rejets = trop senior |
| 5 | **Île-de-France et hybride.** Deux offres sur trois sont en IDF (Paris et Hauts-de-Seine en tête) ; quand la politique de télétravail est précisée, l'hybride domine très largement, le full remote est rare. | **63 %** IDF · hybride **70 %**, full remote 8 % (politique connue) |
| 6 | **Les sources ne se valent pas.** LinkedIn produit 2 à 4 fois moins de bruit que les agrégateurs : 31 % des offres LinkedIn passent le tri contre 8 % pour Adzuna et 5 % pour Jooble. | taux de rétention : LinkedIn **31 %**, HelloWork 18 %, Indeed 12 %, Adzuna 8 %, Jooble 5 % |

**Ce que j'en fais** : cibler les offres « Data Analyst / BI » publiées sur LinkedIn et les sites entreprises, mettre SQL + Power BI + méthode Agile en tête de CV, et traiter les mentions IA comme un prérequis plutôt qu'un bonus.

## Architecture

```
Supabase (PostgreSQL, JobPilot)          Python / pandas                  Modèle en étoile              Restitution
┌──────────────────────┐        ┌──────────────────────────┐      ┌──────────────────────┐     ┌──────────────────┐
│ offers (JSONB)       │        │ src/clean.py             │      │ fact_offers          │     │ Power BI (.pbix) │
│ applications         │ ─CSV─▶ │ · salaires → €/an        │ ───▶ │ bridge_offer_skill   │ ──▶ │ Streamlit/Plotly │
│ status_history       │        │ · lieux → dept → région  │      │ dim_skill, dim_date  │     │ Vues SQL (sql/)  │
│ recommendations      │        │ · 80 compétences (regex) │      │ fact_applications    │     └──────────────────┘
└──────────────────────┘        │ · séniorité, contrat, TT │      │ fact_status_history  │
                                └──────────────────────────┘      │ fact_recommendations │
                                                                  └──────────────────────┘
```

### Nettoyage — les cas réels traités
- **Salaires** : `« À partir de 40K€ »`, `« 28 000,00 €/an - 45 000,00 €/an »`, `« 2 500 € par mois »`, `« 40-45€ brut annuel »` → min / max / médiane en € brut annuel ; les TJM freelance (`« TJM HT max 709 € »`) sont isolés et non convertis.
- **Lieux** : `« 92 - Nanterre »`, `« Paris 01 - 75 »`, `« Lyon (69) »`, `« 93100 Montreuil »`, `« Issy-les-Moulineaux, FR »` → ville, département, région (référentiel de 100+ villes + codes postaux).
- **Séniorité** : texte libre (`« Confirmé (au moins 5 ans d'expérience) »`, `« 3 à 5 ans (alternance comprise) »`) → 3 classes + années minimum.
- **Compétences** : 80 compétences canoniques en 8 familles, détectées par expressions régulières sur les champs structurés (must-have / nice-to-have / mots-clés), avec le niveau d'exigence conservé. Les faux positifs rencontrés (« IA » qui matchait « j'ai » dans le texte brut, « tests » trop générique) ont été corrigés en restreignant la détection aux champs structurés.
- **Sources** : 14 libellés bruts (`« Emplois Glassdoor »`, `« cmacgm-jobnotification@… »`) → 12 sources normalisées.

Un journal de qualité (`data/clean/pipeline_log.json`) donne à chaque exécution les taux de complétude et les lieux non résolus.

## Reproduire

```bash
pip install -r requirements.txt
python src/clean.py                      # data/raw/*.csv  →  data/clean/*.csv
streamlit run app/streamlit_app.py       # dashboard local
```

SQL (PostgreSQL / Supabase) : `sql/01_schema.sql` crée le schéma `jobmarket`, `sql/02_views.sql` les 9 vues analytiques (une par question métier). Chargement : `\copy jobmarket.fact_offers from 'data/clean/fact_offers.csv' csv header`.

Power BI : voir `powerbi/README.md` (relations, mesures DAX dans `powerbi/mesures.dax`).

Tableau Public : voir `tableau/README.md` (relations, champs calculés, 5 feuilles + Story) ; source Excel prête dans le même dossier.

## Limites, à lire avant d'interpréter
- **Échantillon biaisé par ma recherche** : postes Data / BI / Business Analyst, majoritairement Île-de-France, niveau junior à confirmé. Ce n'est pas le marché français complet, et 15 jours de collecte ne font pas une tendance.
- Les champs structurés sont extraits par un LLM (Gemini via JobPilot) : les erreurs d'extraction sont partiellement corrigées par le pipeline, pas éliminées.
- Les offres Indeed / Glassdoor n'exposent souvent que l'extrait de l'annonce : moins de compétences détectées sur ces sources.
- Le salaire n'est affiché que dans 17 % des offres : les médianes sont indicatives.

## Stack
Python 3.13 · pandas · PostgreSQL (Supabase) · Power BI (DAX) · Tableau Public · Streamlit/Plotly · données brutes : exports CSV de JobPilot (Next.js + Supabase).

---
*Juliana Niapoh — Data Analyst / BI · [Portfolio](https://juliana-niapoh-portfolio.netlify.app/) · [LinkedIn](https://www.linkedin.com/in/jniapoh/) · [JobPilot](https://jobpilot-ashy.vercel.app/)*
