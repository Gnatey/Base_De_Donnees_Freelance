# Tableau Public — montage du dashboard (≈ 1 h 30)

Source : `source_marche_emploi_data.xlsx` (7 feuilles = les 7 tables du modèle en étoile). Résultat attendu : un **Story** public de 5 points, un par question métier, reprenant les mêmes constats que le README.

## 1. Connexion (5 min)
1. Tableau Public → *Connecter* → **Microsoft Excel** → `source_marche_emploi_data.xlsx`.
2. Onglet *Source de données* : glisser **Offres** sur le canevas.
3. Ajouter **Offre_Competence** → relation `offer_id = offer_id`, puis **Competences** → relation `skill = skill` (relations Tableau ≥ 2020.2, pas de jointure physique : ça évite de dupliquer les offres).
4. Dans une **seconde source de données** (Nouvelle source → même fichier) : **Offres_recues** seule, puis **Candidatures** + **Historique_statuts** (`application_id`). Garder les sources séparées évite les faux produits cartésiens.
5. Vérifier les types : `salary_min/max/mid` → Nombre (décimal), `collected_at`, `received_at` → Date & heure, `flag_senior`, `is_applied` → Booléen, `department` → **Chaîne** (sinon « 01 » devient 1).

## 2. Champs calculés (copier-coller)
```
// Part des offres (dénominateur = toutes les offres de la source, hors filtre compétence)
Part des offres = COUNTD([offer_id]) / { FIXED : COUNTD([offer_id]) }

// Salaire en k€
Salaire médian (k€) = MEDIAN([salary_mid]) / 1000

// Transparence salariale
Transparence salariale = COUNTD(IF NOT ISNULL([salary_mid]) THEN [offer_id] END) / COUNTD([offer_id])

// Part juniors
Part juniors = SUM(IF [seniority] = "Junior (0-2 ans)" THEN 1 ELSE 0 END) / COUNT([offer_id])

// Indispensable ?
Est indispensable = IF [requirement] = "Indispensable" THEN "Indispensable" ELSE "Souhaitée / mentionnée" END

// (source Offres_recues) Taux de rétention par source
Taux de rétention = SUM(IF [status] = "accepted" THEN 1 ELSE 0 END) / COUNT([recommendation_id])

// (source Offres_recues) Trop senior
Part trop senior = SUM(IF [flag_senior] OR [reject_reason] = "Trop senior" THEN 1 ELSE 0 END) / COUNT([recommendation_id])
```

## 3. Les 5 feuilles + 1 vue d'ensemble

| Feuille | Visuel | Lignes / colonnes | Détail |
|---|---|---|---|
| **KPI** | 5 cartes texte | — | `COUNTD(offer_id)`, `Transparence salariale`, `Salaire médian (k€)`, `Part juniors`, part IDF (`SUM(IF region="Île-de-France")/COUNT`) |
| **Compétences** | Barres horizontales empilées | Lignes `skill` (trié par COUNTD desc, Top 20) · Colonnes `COUNTD(offer_id)` · Couleur `Est indispensable` | Bleu foncé #2A78D6 indispensable, bleu clair #A9C6EC souhaitée. Infobulle : `Part des offres` |
| **Salaires** | Boîte à moustaches | Colonnes `salary_mid` · Lignes `job_family` · Détail `offer_id` | *Analyse → Tracé en boîte*. Filtre `salary_mid` non null. Second visuel : barres `Transparence salariale` par `job_family` |
| **Géographie** | Carte des régions (ou barres) + barres télétravail | Carte : `region` en rôle géographique *État/Province* (France) · Couleur `COUNTD(offer_id)` dégradé bleu. Barres : `remote_policy` × `Part des offres` | Exclure « Non précisé » de la carte, le garder dans les barres (c'est un constat : 53 % des offres ne précisent rien) |
| **Séniorité** | Barres 100 % empilées | Lignes `job_family` · Colonnes `COUNT(offer_id)` → *Calcul rapide → Pourcentage du total* (tableau à travers) · Couleur `seniority` | Ordre couleurs : Junior vert #1BAF7A, Confirmé bleu #2A78D6, Senior orange #EB6834, Non précisé gris #B5B3AD |
| **Entonnoir & sources** | Barres (source Offres_recues) | `source` × `COUNT` et `Taux de rétention` en double barre ; raisons de rejet `reject_reason` × COUNT (filtre status = rejected) | Pas d'entonnoir natif dans Tableau : barres horizontales triées, étiquettes en % |

## 4. Tableau de bord et Story
- **Tableau de bord** « Marché de l'emploi Data » 1200 × 900 (taille fixe, pour un rendu propre sur Tableau Public) : KPI en haut, filtres `job_family` / `region` / `contract_type` en une ligne (*Appliquer à toutes les feuilles utilisant cette source*), puis 2 feuilles par ligne.
- **Story** : 5 points = 5 constats du README, un titre-constat par point (« SQL en tête, loin devant Python » …), chaque point affichant la feuille concernée. C'est ce qui se lit comme une étude, pas comme un tableau.
- Palette : n'utiliser que les couleurs ci-dessus ; texte noir #0B0B0B, grille #E6E5E1 ; pas de couleur pour le texte.

## 5. Publication
*Fichier → Enregistrer sur Tableau Public*. Titre : « Marché de l'emploi Data en France — 172 offres analysées ». Description : la question métier + lien vers ce dépôt. Cocher *Afficher les feuilles en onglets*. Récupérer le lien de partage → l'ajouter au README et au portfolio.

Le même fichier Excel sert au `.pbix` Power BI (`../powerbi/README.md`) : une seule source, trois outils.
