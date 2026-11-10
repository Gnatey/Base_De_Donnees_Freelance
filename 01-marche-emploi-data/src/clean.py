"""
Pipeline de nettoyage — Analyse du marché de l'emploi Data en France
=====================================================================
Entrée  : exports bruts Supabase (data/raw/*.csv)
Sortie  : modèle en étoile prêt pour Power BI / SQL (data/clean/*.csv)

Usage : python src/clean.py
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import pandas as pd

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
OUT = Path(__file__).resolve().parents[1] / "data" / "clean"
OUT.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Référentiels
# ---------------------------------------------------------------------------
DEPT_TO_REGION = {
    **{d: "Île-de-France" for d in ["75", "77", "78", "91", "92", "93", "94", "95"]},
    **{d: "Auvergne-Rhône-Alpes" for d in ["01", "03", "07", "15", "26", "38", "42", "43", "63", "69", "73", "74"]},
    **{d: "Provence-Alpes-Côte d'Azur" for d in ["04", "05", "06", "13", "83", "84"]},
    **{d: "Occitanie" for d in ["09", "11", "12", "30", "31", "32", "34", "46", "48", "65", "66", "81", "82"]},
    **{d: "Nouvelle-Aquitaine" for d in ["16", "17", "19", "23", "24", "33", "40", "47", "64", "79", "86", "87"]},
    **{d: "Hauts-de-France" for d in ["02", "59", "60", "62", "80"]},
    **{d: "Grand Est" for d in ["08", "10", "51", "52", "54", "55", "57", "67", "68", "88"]},
    **{d: "Pays de la Loire" for d in ["44", "49", "53", "72", "85"]},
    **{d: "Bretagne" for d in ["22", "29", "35", "56"]},
    **{d: "Normandie" for d in ["14", "27", "50", "61", "76"]},
    **{d: "Bourgogne-Franche-Comté" for d in ["21", "25", "39", "58", "70", "71", "89", "90"]},
    **{d: "Centre-Val de Loire" for d in ["18", "28", "36", "37", "41", "45"]},
    **{d: "Corse" for d in ["2A", "2B", "20"]},
}

CITY_TO_DEPT = {
    "paris": "75", "lyon": "69", "villeurbanne": "69", "marseille": "13", "vitrolles": "13", "aix-en-provence": "13",
    "toulouse": "31", "blagnac": "31", "nantes": "44", "bordeaux": "33", "lille": "59", "rennes": "35", "bruz": "35",
    "strasbourg": "67", "montpellier": "34", "nice": "06", "sophia antipolis": "06", "grenoble": "38", "dijon": "21",
    "rouen": "76", "le havre": "76", "tours": "37", "orleans": "45", "angers": "49", "le mans": "72", "brest": "29",
    "nancy": "54", "metz": "57", "reims": "51", "caen": "14", "clermont-ferrand": "63", "limoges": "87", "poitiers": "86",
    "niort": "79", "la rochelle": "17", "pau": "64", "bayonne": "64", "perpignan": "66", "nimes": "30", "avignon": "84",
    "annecy": "74", "chambery": "73", "valence": "26", "saint-etienne": "42", "besancon": "25", "mulhouse": "68",
    "amiens": "80", "dunkerque": "59", "roubaix": "59", "tourcoing": "59", "valenciennes": "59",
    # Île-de-France
    "issy-les-moulineaux": "92", "levallois-perret": "92", "courbevoie": "92", "nanterre": "92", "puteaux": "92",
    "neuilly-sur-seine": "92", "boulogne-billancourt": "92", "la garenne-colombes": "92", "montrouge": "92",
    "antony": "92", "la defense": "92", "rueil-malmaison": "92", "suresnes": "92", "clichy": "92", "gennevilliers": "92",
    "colombes": "92", "asnieres-sur-seine": "92", "chatillon": "92", "malakoff": "92", "vanves": "92", "meudon": "92",
    "sevres": "92", "clamart": "92", "bagneux": "92", "fontenay-aux-roses": "92", "le plessis-robinson": "92",
    "velizy-villacoublay": "78", "versailles": "78", "saint-quentin-en-yvelines": "78", "guyancourt": "78",
    "montigny-le-bretonneux": "78", "poissy": "78", "saint-germain-en-laye": "78",
    "montreuil": "93", "saint-denis": "93", "bagnolet": "93", "pantin": "93", "aubervilliers": "93", "bobigny": "93",
    "saint-ouen": "93", "noisy-le-grand": "93", "rosny-sous-bois": "93", "la plaine saint-denis": "93",
    "saint-maur-des-fosses": "94", "creteil": "94", "ivry-sur-seine": "94", "vitry-sur-seine": "94", "vincennes": "94",
    "charenton-le-pont": "94", "rungis": "94", "orly": "94", "maisons-alfort": "94", "fontenay-sous-bois": "94",
    "champs-sur-marne": "77", "montevrain": "77", "marne-la-vallee": "77", "serris": "77", "melun": "77", "meaux": "77",
    "lisses": "91", "evry": "91", "massy": "91", "palaiseau": "91", "les ulis": "91", "saclay": "91", "orsay": "91",
    "cergy": "95", "roissy-en-france": "95", "argenteuil": "95",
    "bouguenais": "44", "bretigny-sur-orge": "91", "chartres": "28", "chilly-mazarin": "91", "colmar": "68", "le kremlin-bicetre": "94",
    "les mureaux": "78", "lieusaint": "77", "limonest": "69", "liepvre": "68", "montereau-sur-le-jard": "77", "nucourt": "95", "osny": "95",
    "plerin": "22", "venelles": "13", "villeneuve-d'ascq": "59", "eragny": "95", "cesson-sevigne": "35", "saint-herblain": "44",
    "merignac": "33", "pessac": "33", "labege": "31", "colomiers": "31", "ecully": "69", "bron": "69", "lille": "59", "marcq-en-baroeul": "59",
}

REGION_ALIASES = {
    "ile-de-france": "Île-de-France", "idf": "Île-de-France",
    "auvergne-rhone-alpes": "Auvergne-Rhône-Alpes", "rhone-alpes": "Auvergne-Rhône-Alpes",
    "provence-alpes-cote d'azur": "Provence-Alpes-Côte d'Azur", "paca": "Provence-Alpes-Côte d'Azur",
    "occitanie": "Occitanie", "nouvelle-aquitaine": "Nouvelle-Aquitaine", "hauts-de-france": "Hauts-de-France",
    "grand est": "Grand Est", "pays de la loire": "Pays de la Loire", "bretagne": "Bretagne", "normandie": "Normandie",
    "bourgogne-franche-comte": "Bourgogne-Franche-Comté", "centre-val de loire": "Centre-Val de Loire",
}

# Taxonomie de compétences : canonique -> regex (insensible à la casse, sur texte normalisé)
SKILLS = {
    # BI & visualisation
    "Power BI": r"power ?bi", "DAX": r"\bdax\b", "Power Query": r"power ?query", "Tableau": r"\btableau( software| desktop)?\b",
    "Qlik": r"\bqlik", "Looker": r"\blooker", "SSRS": r"\bssrs\b", "Excel": r"\bexcel\b", "VBA": r"\bvba\b",
    "Google Analytics": r"google analytics|\bga4\b", "Data Studio / Looker Studio": r"data studio|looker studio",
    # Langages
    "SQL": r"\bsql\b", "Python": r"\bpython\b", "R": r"\br\b(?= ?[,/(]| et | ou |$)", "Java": r"\bjava\b(?!script)",
    "Scala": r"\bscala\b", "JavaScript": r"javascript|\bjs\b", ".NET / C#": r"\.net\b|\bc#", "SAS": r"\bsas\b",
    "Shell / Bash": r"\bbash\b|\bshell\b",
    # Bases de données
    "PostgreSQL": r"postgres", "MySQL": r"mysql", "SQL Server": r"sql server|\bt-sql\b|\bssms\b", "Oracle": r"\boracle\b",
    "MongoDB / NoSQL": r"mongo|nosql", "BigQuery": r"bigquery", "Snowflake": r"snowflake", "Redshift": r"redshift",
    "Databricks": r"databricks", "Teradata": r"teradata",
    # Data engineering
    "ETL": r"\betl\b|\belt\b", "SSIS": r"\bssis\b", "Talend": r"talend", "Informatica": r"informatica",
    "Airflow": r"airflow", "dbt": r"\bdbt\b", "Spark": r"\bspark\b|pyspark", "Kafka": r"kafka", "Hadoop": r"hadoop",
    "Dataiku": r"dataiku", "Alteryx": r"alteryx", "Data Factory": r"data factory", "Semarchy": r"semarchy",
    "Data Warehouse": r"data ?warehouse|entrep[oô]t de donn", "Data Lake": r"data ?lake", "Modélisation de données": r"mod[eé]lisation",
    # Cloud
    "Azure": r"\bazure\b", "AWS": r"\baws\b|amazon web services", "GCP": r"\bgcp\b|google cloud", "Fabric": r"microsoft fabric|\bfabric\b",
    # Data science / IA
    "Machine Learning": r"machine learning|\bml\b|apprentissage automatique", "IA / LLM": r"intelligence artificielle|\bllm|gen ?ai|ia g[eé]n[eé]rative|\bia\b(?! ?\d)|chatgpt|copilot",
    "Statistiques": r"statisti", "NLP": r"\bnlp\b",
    # Gouvernance / qualité
    "Data Quality": r"data quality|qualit[eé] des donn", "Data Governance": r"gouvernance|data governance", "RGPD": r"\brgpd\b|\bgdpr\b",
    "MDM": r"\bmdm\b|master data",
    # Métier / méthodes
    "Agile / Scrum": r"\bagile|scrum|\bsafe\b", "Jira": r"\bjira\b", "Confluence": r"confluence", "Git": r"\bgit(hub|lab)?\b",
    "Recueil de besoins": r"recueil|besoins? m[eé]tier|expression de besoin", "Spécifications fonctionnelles": r"sp[eé]cifications?|cahier des charges",
    "Recette / Tests": r"recette|tests? (fonctionnel|unitaire|d.acceptation|utilisateur)|\buat\b|\bqa\b", "Gestion de projet": r"gestion de projet|chef de projet|project manag",
    "SAP": r"\bsap\b", "Salesforce": r"salesforce", "ERP": r"\berp\b", "CRM": r"\bcrm\b",
    "Anglais": r"anglais|english|bilingue",
    # Finance
    "Contrôle de gestion": r"contr[oô]le de gestion|controlling",
}
SKILL_FAMILY = {
    **{s: "BI & visualisation" for s in ["Power BI", "DAX", "Power Query", "Tableau", "Qlik", "Looker", "SSRS", "Excel", "VBA", "Google Analytics", "Data Studio / Looker Studio"]},
    **{s: "Langages" for s in ["SQL", "Python", "R", "Java", "Scala", "JavaScript", ".NET / C#", "SAS", "Shell / Bash"]},
    **{s: "Bases de données" for s in ["PostgreSQL", "MySQL", "SQL Server", "Oracle", "MongoDB / NoSQL", "BigQuery", "Snowflake", "Redshift", "Databricks", "Teradata"]},
    **{s: "Data engineering" for s in ["ETL", "SSIS", "Talend", "Informatica", "Airflow", "dbt", "Spark", "Kafka", "Hadoop", "Dataiku", "Alteryx", "Data Factory", "Semarchy", "Data Warehouse", "Data Lake", "Modélisation de données"]},
    **{s: "Cloud" for s in ["Azure", "AWS", "GCP", "Fabric"]},
    **{s: "Data science / IA" for s in ["Machine Learning", "IA / LLM", "Statistiques", "NLP"]},
    **{s: "Gouvernance & qualité" for s in ["Data Quality", "Data Governance", "RGPD", "MDM"]},
    **{s: "Méthodes & métier" for s in ["Agile / Scrum", "Jira", "Confluence", "Git", "Recueil de besoins", "Spécifications fonctionnelles", "Recette / Tests", "Gestion de projet", "SAP", "Salesforce", "ERP", "CRM", "Anglais", "Contrôle de gestion"]},
}

JOB_FAMILIES = [  # ordre = priorité
    ("Data Scientist", r"data scien|scientist|machine learning|\bml engineer|ing[eé]nieur(e)? ia\b|\bia\b|intelligence artificielle"),
    ("Data Engineer", r"data engineer|ing[eé]nieur data|data ing|dataops|engineer data|developpeur data|développeur data"),
    ("Consultant / Développeur BI", r"\bbi\b|business intelligence|power ?bi|tableau|qlik|d[eé]cisionnel|dataviz|data viz"),
    ("Data Analyst", r"data analy|analyste? data|analyste? de donn|data & analytics|analytics engineer|analyste d[eé]cisionnel|analyste? bi|etudes statistiques|statisticien|charge d.etudes"),
    ("Business Analyst / AMOA", r"business analyst|\bamoa\b|\bmoa\b|analyste fonctionnel|product owner|\bpo\b|proxy"),
    ("Chef de projet / PMO", r"chef(fe)? de projet|project manager|\bpmo\b|scrum master|coordinat"),
    ("Contrôle de gestion / Finance", r"contr[oô]l|finance|comptab|financier|business controller"),
    ("Data Manager / Gouvernance", r"data manager|data steward|data owner|gouvernance|data governance|data quality|\bmdm\b|data product"),
    ("Autre Data", r"\bdata\b|donn[eé]es"),
]

SENIORITY_ORDER = ["Junior (0-2 ans)", "Confirmé (3-5 ans)", "Senior (5 ans et +)", "Non précisé"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def norm(s) -> str:
    """minuscule, sans accents, espaces normalisés"""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    s = str(s).replace(" ", " ").replace("\xa0", " ").replace("‑", "-").replace("‑", "-")
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()


def load_json(s):
    try:
        v = json.loads(s)
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}


def parse_salary(text: str) -> tuple[float | None, float | None, str]:
    """Retourne (min_annuel, max_annuel, source_format) en € brut annuel."""
    t = norm(text)
    if not t or "aucun" in t or "non" in t[:10] or "selon profil" == t or "fonction du profil" in t:
        return None, None, "non précisé"
    # supprime les séparateurs de milliers "28 000,00" -> "28000"
    t2 = re.sub(r"(\d)[ .](?=\d{3}\b)", r"\1", t)
    t2 = t2.replace(",00", "")
    nums = [float(x.replace(",", ".")) for x in re.findall(r"\d+(?:[.,]\d+)?", t2)]
    if not nums:
        return None, None, "non précisé"
    monthly = "mois" in t2 or "mensuel" in t2
    daily = "jour" in t2 or "tjm" in t2 or "/j" in t2
    has_k = "k" in t2
    vals = []
    for n in nums:
        if n < 10:      # "2 ans", "H/F" etc. -> bruit
            continue
        if has_k and n < 500:
            n *= 1000
        elif n < 200:   # "40-45€ brut annuel" -> 40k
            n *= 1000
        elif n < 10000 and monthly:
            n *= 12
        elif daily and 200 <= n <= 2000:
            pass        # TJM freelance : gardé tel quel (€/jour), non converti en salaire
        elif n < 10000:
            continue    # valeur ambiguë
        vals.append(n)
    if daily:
        vals = [v for v in vals if 200 <= v <= 2000]
        return (min(vals), max(vals), "journalier (TJM)") if vals else (None, None, "non exploitable")
    vals = [v for v in vals if 15000 <= v <= 250000]
    if not vals:
        return None, None, "non exploitable"
    return min(vals), max(vals), "mensuel" if monthly else "annuel"


def parse_seniority(text: str) -> tuple[str, float | None]:
    t = norm(text)
    if not t or "non precise" in t:
        return "Non précisé", None
    years = [float(x) for x in re.findall(r"(\d+(?:[.,]\d+)?)\s*(?:a|à|-|ans?)", t)]
    years = [y for y in years if y <= 20]
    y = min(years) if years else None
    if "junior" in t or "debutant" in t or "jeune diplome" in t:
        return "Junior (0-2 ans)", y
    if y is not None:
        if y <= 2:
            return "Junior (0-2 ans)", y
        if y <= 5:
            return "Confirmé (3-5 ans)", y
        return "Senior (5 ans et +)", y
    if "senior" in t or "expert" in t or "lead" in t:
        return "Senior (5 ans et +)", None
    if "confirme" in t or "intermediaire" in t or "experimente" in t:
        return "Confirmé (3-5 ans)", None
    return "Non précisé", None


def parse_location(text: str) -> tuple[str, str, str]:
    """Retourne (ville, département, région)."""
    t = norm(text)
    if not t:
        return "Non précisé", "Non précisé", "Non précisé"
    if "suisse" in t or "switzerland" in t or "geneve" in t or "lausanne" in t:
        return text.strip(), "Étranger", "Étranger"
    if "belgique" in t or "luxembourg" in t or "bruxelles" in t:
        return text.strip(), "Étranger", "Étranger"
    if "teletravail" in t and len(t) < 20 or t in ("remote", "full remote", "100% remote"):
        return "Télétravail", "Télétravail", "Télétravail"
    if t in ("france", "france entiere", "national", "toute la france"):
        return "France entière", "Non précisé", "France entière"
    # code postal 5 chiffres ou département "(92)" / "92 -" / "- 75"
    m = re.search(r"\b(\d{5})\b", t)
    dept = None
    if m:
        dept = m.group(1)[:2]
    else:
        m = re.search(r"\((\d{2})\)|^(\d{2})\s*-|-\s*(\d{2})\b|\b(\d{2})\s*-", t)
        if m:
            dept = next(g for g in m.groups() if g)
    if dept in ("20",):
        dept = "2A"
    # ville : premier segment alphabétique
    city_raw = re.split(r"[,(/]|\s-\s|\d", text.replace("‑", "-"))[0].strip(" -")
    city = city_raw.title() if city_raw else "Non précisé"
    if dept is None:
        tn = norm(city_raw)
        tn = re.sub(r"^ville de ", "", tn)
        tn = re.sub(r" \d+e?r?$", "", tn)          # "paris 6e"
        for alias, reg in REGION_ALIASES.items():
            if alias in t:
                return (city if tn not in alias else "Non précisé"), "Non précisé", reg
        dept = CITY_TO_DEPT.get(tn)
        if dept is None:
            for k, v in CITY_TO_DEPT.items():       # correspondance partielle
                if k in t:
                    dept = v
                    break
    if dept is None:
        return city, "Non précisé", "Non précisé"
    return city, dept, DEPT_TO_REGION.get(dept, "Non précisé")


def parse_remote(text: str) -> str:
    t = norm(text)
    if not t:
        return "Non précisé"
    if "full" in t or t in ("teletravail", "remote", "100% teletravail", "100%"):
        return "Télétravail complet"
    if "hybride" in t or "partiel" in t or "occasionnel" in t or re.search(r"\d", t):
        return "Hybride"
    if "presentiel" in t or "sur site" in t or "on site" in t:
        return "Présentiel"
    return "Non précisé"


def parse_contract(text: str) -> str:
    t = norm(text)
    if not t:
        return "Non précisé"
    if "cdi" in t or "full_time" in t or "temps plein" in t or "permanent" in t:
        return "CDI"
    if "cdd" in t or "temporary" in t:
        return "CDD"
    if "intern" in t or "stage" in t:
        return "Stage"
    if "alternance" in t or "apprenti" in t:
        return "Alternance"
    if "interim" in t:
        return "Intérim"
    if "freelance" in t or "independant" in t or "portage" in t or "mission" in t:
        return "Freelance"
    return "Autre"


def job_family(title: str) -> str:
    t = norm(title)
    for fam, rx in JOB_FAMILIES:
        if re.search(rx, t):
            return fam
    return "Autre IT / Support"


def company_type(analysis: dict, raw: str) -> str:
    ct = norm(analysis.get("company_type"))
    if "esn" in ct or "conseil" in ct or "cabinet" in ct or "ssii" in ct:
        return "ESN / Conseil"
    if "startup" in ct or "scale" in ct:
        return "Start-up / Scale-up"
    if "grand" in ct or "groupe" in ct or "grande" in ct:
        return "Grand groupe"
    if "pme" in ct or "eti" in ct:
        return "PME / ETI"
    if "public" in ct or "administration" in ct or "collectivit" in ct:
        return "Secteur public"
    if "recrut" in ct or "interim" in ct:
        return "Cabinet de recrutement"
    return "Non précisé"


def extract_skills(texts: list[str]) -> set[str]:
    t = " ".join(norm(x) for x in texts if x)
    return {s for s, rx in SKILLS.items() if re.search(rx, t)}


def normalize_source(s: str) -> str:
    t = norm(s)
    if "linkedin" in t:
        return "LinkedIn"
    if "indeed" in t:
        return "Indeed"
    if "hellowork" in t:
        return "HelloWork"
    if "france travail" in t or "pole emploi" in t:
        return "France Travail"
    if "glassdoor" in t:
        return "Glassdoor"
    if "adzuna" in t:
        return "Adzuna"
    if "wttj" in t or "welcome" in t:
        return "Welcome to the Jungle"
    if "apec" in t:
        return "APEC"
    if "jooble" in t:
        return "Jooble"
    if "efinancial" in t or "dogfinance" in t:
        return "Jobboards finance"
    if "site entreprise" in t or "jobs2web" in t or "noreply" in t or "notification" in t:
        return "Site entreprise"
    if "engagement jeunes" in t or "tekkit" in t or "consultant independant" in t:
        return "Autres jobboards"
    if t in ("texte", "autre", ""):
        return "Saisie manuelle"
    return s.strip()


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
def build():
    offers = pd.read_csv(RAW / "offers.csv")
    apps = pd.read_csv(RAW / "applications.csv")
    hist = pd.read_csv(RAW / "status_history.csv")
    reco = pd.read_csv(RAW / "recommendations.csv")
    log = {"offers_raw": len(offers), "applications_raw": len(apps), "status_history_raw": len(hist), "recommendations_raw": len(reco)}

    # ---- Offres ------------------------------------------------------------
    offers["extracted_d"] = offers["extracted"].map(load_json)
    offers["analysis_d"] = offers["analysis"].map(load_json)

    rows, skill_rows = [], []
    for _, o in offers.iterrows():
        e, a = o["extracted_d"], o["analysis_d"]
        title = o["title"] if pd.notna(o["title"]) and str(o["title"]).strip() else e.get("title", "")
        company = o["company"] if pd.notna(o["company"]) and str(o["company"]).strip() else e.get("company", "")
        loc = o["location"] if pd.notna(o["location"]) and str(o["location"]).strip() else e.get("location", "")
        contract = o["contract"] if pd.notna(o["contract"]) and str(o["contract"]).strip() else e.get("contract", "")
        sal_min, sal_max, sal_fmt = parse_salary(e.get("salary", ""))
        sen_label, sen_years = parse_seniority(e.get("seniority", ""))
        city, dept, region = parse_location(loc)
        skills_must = extract_skills(e.get("must_have", []) + e.get("keywords", []))
        skills_nice = extract_skills(e.get("nice_to_have", [])) - skills_must
        skills_all = skills_must | skills_nice
        created = pd.to_datetime(o["created_at"], utc=True, format="ISO8601")
        rows.append({
            "offer_id": o["id"],
            "title": str(title).strip() or "Non précisé",
            "job_family": job_family(title),
            "company": str(company).strip() or "Non précisé",
            "company_type": company_type(a, o.get("raw_text", "")),
            "sector": (e.get("domain") or "Non précisé").strip() or "Non précisé",
            "source": normalize_source(o["source"]),
            "contract_type": parse_contract(contract),
            "remote_policy": parse_remote(e.get("remote", "")),
            "city": city, "department": dept, "region": region,
            "salary_min": sal_min, "salary_max": sal_max,
            "salary_mid": (sal_min + sal_max) / 2 if (sal_min and sal_fmt != "journalier (TJM)") else None,
            "tjm_max": sal_max if sal_fmt == "journalier (TJM)" else None,
            "salary_format": sal_fmt,
            "seniority": sen_label, "min_years_experience": sen_years,
            "n_must_have": len(e.get("must_have", [])), "n_nice_to_have": len(e.get("nice_to_have", [])),
            "n_red_flags": len(e.get("red_flags", [])),
            "n_skills_detected": len(skills_all),
            "match_score": o["score"],
            "score_hard_skills": (a.get("breakdown", {}).get("hard_skills") or {}).get("score"),
            "score_experience": (a.get("breakdown", {}).get("experience") or {}).get("score"),
            "score_logistics": (a.get("breakdown", {}).get("logistics") or {}).get("score"),
            "ai_should_apply": a.get("should_apply", ""),
            "decision": o["decision"] if pd.notna(o["decision"]) else "pending",
            "reject_reason": o["reject_reason"] if pd.notna(o["reject_reason"]) else "",
            "collected_at": created,
            "collected_date": created.date(),
            "collected_week": created.strftime("%G-S%V"),
        })
        for s in skills_all:
            skill_rows.append({"offer_id": o["id"], "skill": s, "skill_family": SKILL_FAMILY.get(s, "Autre"),
                               "requirement": "Indispensable" if s in skills_must else "Souhaité" if s in skills_nice else "Mentionné"})

    fact_offers = pd.DataFrame(rows)
    bridge_skills = pd.DataFrame(skill_rows)
    dim_skill = (bridge_skills.groupby(["skill", "skill_family"]).size().reset_index(name="n_offers")
                 .sort_values("n_offers", ascending=False))

    # ---- Candidatures -------------------------------------------------------
    apps["status_label"] = apps["status"].map({
        "a_postuler": "À postuler", "postule": "Postulé", "entretien": "Entretien", "refuse": "Refusé",
        "abandonne": "Abandonné", "expiree": "Expirée", "accepte": "Accepté", "offre": "Offre reçue",
    }).fillna(apps["status"])
    fact_apps = pd.DataFrame({
        "application_id": apps["id"], "offer_id": apps["offer_id"],
        "company": apps["company"], "title": apps["title"], "job_family": apps["title"].map(job_family),
        "channel": apps["channel"].map(normalize_source), "status": apps["status"], "status_label": apps["status_label"],
        "cv_variant": apps["cv_variant"].fillna("Non précisé"), "match_score": apps["score"],
        "created_at": pd.to_datetime(apps["created_at"], utc=True, format="ISO8601"),
        "applied_at": pd.to_datetime(apps["applied_at"], errors="coerce"),
        "updated_at": pd.to_datetime(apps["updated_at"], utc=True, format="ISO8601"),
        "last_email_at": pd.to_datetime(apps["last_email_at"], utc=True, format="ISO8601", errors="coerce"),
    })
    loc = apps["location"].map(parse_location)
    fact_apps["city"], fact_apps["department"], fact_apps["region"] = [x[0] for x in loc], [x[1] for x in loc], [x[2] for x in loc]
    fact_apps["is_applied"] = fact_apps["status"].isin(["postule", "entretien", "refuse", "accepte", "offre"])
    fact_apps["days_to_apply"] = (fact_apps["applied_at"].dt.tz_localize("UTC") - fact_apps["created_at"]).dt.days

    # ---- Historique des statuts (délais) -----------------------------------
    hist["changed_at"] = pd.to_datetime(hist["changed_at"], utc=True, format="ISO8601")
    hist = hist.sort_values(["application_id", "changed_at"])
    hist["from_status"] = hist["from_status"].replace("null", pd.NA)
    hist["prev_changed_at"] = hist.groupby("application_id")["changed_at"].shift(1)
    hist["days_in_previous_status"] = (hist["changed_at"] - hist["prev_changed_at"]).dt.total_seconds() / 86400
    fact_hist = hist[["id", "application_id", "from_status", "to_status", "changed_at", "days_in_previous_status"]].rename(columns={"id": "history_id"})

    # ---- Recommandations (flux entrant) ------------------------------------
    reco["reject_reason_label"] = reco["reject_reason"].fillna("").map(lambda r: {
        "trop_senior": "Trop senior", "expiree": "Expirée", "metier": "Hors métier", "fit_metier": "Hors métier",
        "contrat": "Type de contrat", "lieu": "Localisation", "salaire": "Salaire", "secteur": "Secteur",
        "entreprise": "Entreprise", "doublon": "Doublon",
    }.get(r, "Autre" if r else ""))
    rloc = reco["location"].map(parse_location)
    fact_reco = pd.DataFrame({
        "recommendation_id": reco["id"], "offer_id": reco["offer_id"], "source": reco["source"].map(normalize_source), "origin": reco["origin"],
        "title": reco["title"], "job_family": reco["title"].map(job_family), "company": reco["company"],
        "city": [x[0] for x in rloc], "department": [x[1] for x in rloc], "region": [x[2] for x in rloc],
        "quick_score": reco["quick_score"], "status": reco["status"], "reject_reason": reco["reject_reason_label"],
        "flag_senior": reco["senior"].astype(str).str.lower().eq("true"),
        "received_at": pd.to_datetime(reco["received_at"], utc=True, format="ISO8601"),
        "decided_at": pd.to_datetime(reco["decided_at"], utc=True, format="ISO8601", errors="coerce"),
    })
    fact_reco["received_date"] = fact_reco["received_at"].dt.date
    fact_reco["hours_to_decision"] = (fact_reco["decided_at"] - fact_reco["received_at"]).dt.total_seconds() / 3600

    # ---- Dimension date ----------------------------------------------------
    all_dates = pd.concat([pd.Series(fact_offers["collected_at"]), fact_apps["created_at"], fact_reco["received_at"]])
    dmin, dmax = all_dates.min().normalize(), all_dates.max().normalize()
    dim_date = pd.DataFrame({"date": pd.date_range(dmin, dmax, freq="D").date})
    dd = pd.to_datetime(dim_date["date"])
    dim_date["year"], dim_date["month"], dim_date["month_name"] = dd.dt.year, dd.dt.month, dd.dt.strftime("%B")
    dim_date["week"] = dd.dt.strftime("%G-S%V")
    dim_date["weekday"] = dd.dt.day_name()
    dim_date["is_weekend"] = dd.dt.weekday >= 5

    # ---- Sorties -----------------------------------------------------------
    outputs = {
        "fact_offers": fact_offers, "bridge_offer_skill": bridge_skills, "dim_skill": dim_skill,
        "fact_applications": fact_apps, "fact_status_history": fact_hist, "fact_recommendations": fact_reco, "dim_date": dim_date,
    }
    for name, df in outputs.items():
        df.to_csv(OUT / f"{name}.csv", index=False, encoding="utf-8-sig")
        log[name] = len(df)

    # ---- Journal qualité ---------------------------------------------------
    dq = {
        "offres_avec_salaire": int(fact_offers["salary_mid"].notna().sum()),
        "offres_avec_seniorite": int((fact_offers["seniority"] != "Non précisé").sum()),
        "offres_avec_region": int((~fact_offers["region"].isin(["Non précisé"])).sum()),
        "offres_hors_data": int((fact_offers["job_family"] == "Autre IT / Support").sum()),
        "lieux_non_resolus": sorted(fact_offers.loc[fact_offers["region"] == "Non précisé", "city"].unique().tolist()),
    }
    (OUT / "pipeline_log.json").write_text(json.dumps({"rows": log, "data_quality": dq}, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps({"rows": log, "data_quality": dq}, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    build()
