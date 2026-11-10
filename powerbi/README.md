# Rapport Power BI — mode d'emploi

Le fichier `.pbix` se construit sur Windows avec Power BI Desktop (gratuit). Tout ce qu'il faut est ici.

## 1. Charger les données
`Accueil → Obtenir des données → Texte/CSV`, pour chaque fichier de `data/clean/` :

| Table | Rôle |
|---|---|
| `fact_offers` | fait principal (1 ligne = 1 offre) |
| `bridge_offer_skill` | pont offre ↔ compétence (n lignes par offre) |
| `dim_skill` | dimension compétence (famille, volume) |
| `dim_date` | dimension date → **Marquer comme table de dates** |
| `fact_applications` | candidatures suivies |
| `fact_status_history` | transitions de statut (délais) |
| `fact_recommendations` | flux d'offres reçues (alertes + recherches) |

Dans Power Query : forcer les types (`salary_*` → nombre décimal, `*_at` → date/heure, `*_date` → date, `flag_senior` / `is_applied` → vrai/faux). Encodage UTF-8 (BOM inclus dans les CSV).

## 2. Relations (vue Modèle)
- `dim_date[date]` 1 → * `fact_offers[collected_date]` (active)
- `dim_date[date]` 1 → * `fact_recommendations[received_date]` (active)
- `fact_offers[offer_id]` 1 → * `bridge_offer_skill[offer_id]`
- `dim_skill[skill]` 1 → * `bridge_offer_skill[skill]`
- `fact_applications[application_id]` 1 → * `fact_status_history[application_id]`
- `fact_offers[offer_id]` 1 → * `fact_applications[offer_id]` (beaucoup de nulls : laisser à sens unique)

Direction de filtre : simple partout, sauf `bridge_offer_skill` → `fact_offers` en **bidirectionnel** (pour filtrer les offres par compétence).

## 3. Mesures
Copier-coller `mesures.dax` (une mesure à la fois, ou via l'outil externe *Tabular Editor*).

## 4. Pages du rapport (même logique que le Streamlit)
1. **Vue d'ensemble** — 5 cartes KPI (`Nb offres`, `% transparence salariale`, `Salaire médian (k€)`, `% juniors`, `% Île-de-France`) + courbe hebdo.
2. **Compétences** — barres empilées Top 20 (`% indispensable`), matrice famille de poste × compétence avec mise en forme conditionnelle.
3. **Salaires** — boîte à moustaches (visuel *Box and Whisker* du marketplace) ou barres min/max par famille ; barres `% transparence salariale`.
4. **Géographie** — carte *Forme* (régions) ou barres par région ; anneau télétravail ; zoom IDF par département.
5. **Séniorité** — barres 100 % empilées par famille ; histogramme `min_years_experience`.
6. **Entonnoir** — visuel *Entonnoir* natif (offres reçues → analysées → validées → envoyées → entretiens) ; barres raisons de rejet ; `Taux de rétention source`.

Segments communs (volet filtre synchronisé) : `job_family`, `region`, `contract_type`, `dim_date[week]`.

## 5. Partage
Power BI Service demande un compte professionnel/école. Sans compte : exporter chaque page en PDF (`Fichier → Exporter → PDF`) et déposer le `.pbix` + les captures dans ce dossier. La version interactive publique est le Streamlit.
