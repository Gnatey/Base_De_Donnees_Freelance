"""
Dashboard — Marché de l'emploi Data en France
Streamlit + Plotly, alimenté par le modèle en étoile (data/clean/*.csv)
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATA = Path(__file__).resolve().parents[1] / "data" / "clean"

# Palette catégorielle validée (ordre fixe, jamais cyclé)
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
BLUE_SEQ = ["#dbe8f8", "#a9c6ec", "#6fa1e1", "#2a78d6", "#1b5099"]
TEXT, TEXT2, GRID = "#0b0b0b", "#52514e", "#e6e5e1"

st.set_page_config(page_title="Marché de l'emploi Data — France", page_icon="📊", layout="wide")

st.markdown(
    """<style>
    .block-container{padding-top:1.4rem}
    [data-testid="stMetric"]{background:#f6f5f2;border-radius:10px;padding:12px 16px;border:1px solid #e6e5e1}
    [data-testid="stMetricLabel"]{color:#52514e}
    h1,h2,h3{letter-spacing:-.01em}
    </style>""",
    unsafe_allow_html=True,
)


@st.cache_data
def load():
    t = {n: pd.read_csv(DATA / f"{n}.csv") for n in
         ["fact_offers", "bridge_offer_skill", "dim_skill", "fact_applications", "fact_status_history", "fact_recommendations"]}
    t["fact_offers"]["collected_at"] = pd.to_datetime(t["fact_offers"]["collected_at"], utc=True, format="ISO8601")
    t["fact_recommendations"]["received_at"] = pd.to_datetime(t["fact_recommendations"]["received_at"], utc=True, format="ISO8601")
    return t


T = load()
offers, bridge, apps, hist, reco = T["fact_offers"], T["bridge_offer_skill"], T["fact_applications"], T["fact_status_history"], T["fact_recommendations"]


def style(fig, h=380, legend=True):
    fig.update_layout(
        height=h, margin=dict(l=10, r=10, t=36, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, size=13), title_font=dict(size=15, color=TEXT),
        legend=dict(orientation="h", y=-0.18, x=0, font=dict(color=TEXT2)) if legend else dict(visible=False),
        hoverlabel=dict(bgcolor="white", font_color=TEXT),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor=GRID, tickfont=dict(color=TEXT2), title_font=dict(color=TEXT2))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, tickfont=dict(color=TEXT2), title_font=dict(color=TEXT2))
    return fig


# --------------------------------------------------------------------- Filtres
st.title("Marché de l'emploi Data en France")
st.caption("Étude construite à partir d'offres collectées et analysées via JobPilot (LinkedIn, Indeed, HelloWork, France Travail, sites entreprises…). "
           "Un dashboard = une question métier par onglet.")

f1, f2, f3, f4 = st.columns([2, 2, 2, 1.2])
fam_opts = offers["job_family"].value_counts().index.tolist()
fam = f1.multiselect("Famille de poste", fam_opts, default=[])
reg_opts = offers["region"].value_counts().index.tolist()
reg = f2.multiselect("Région", reg_opts, default=[])
ctr_opts = offers["contract_type"].value_counts().index.tolist()
ctr = f3.multiselect("Contrat", ctr_opts, default=[])
show_table = f4.toggle("Vue tableau", value=False, help="Affiche les données sous chaque graphique")

mask = pd.Series(True, index=offers.index)
if fam:
    mask &= offers["job_family"].isin(fam)
if reg:
    mask &= offers["region"].isin(reg)
if ctr:
    mask &= offers["contract_type"].isin(ctr)
O = offers[mask]
B = bridge[bridge["offer_id"].isin(O["offer_id"])]
n = len(O)

# --------------------------------------------------------------------- KPI
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Offres analysées", f"{n}")
pct_sal = 100 * O["salary_mid"].notna().mean() if n else 0
k2.metric("Offres avec salaire affiché", f"{pct_sal:.0f} %")
med = O["salary_mid"].median()
k3.metric("Salaire médian (brut/an)", f"{med/1000:.0f} k€" if pd.notna(med) else "n/a")
pct_junior = 100 * (O["seniority"] == "Junior (0-2 ans)").mean() if n else 0
k4.metric("Offres ouvertes aux juniors", f"{pct_junior:.0f} %")
pct_idf = 100 * (O["region"] == "Île-de-France").mean() if n else 0
k5.metric("Part Île-de-France", f"{pct_idf:.0f} %")

tabs = st.tabs(["Compétences", "Salaires", "Géographie & télétravail", "Séniorité", "Entonnoir & sources", "Méthode"])

# --------------------------------------------------------------------- Compétences
with tabs[0]:
    st.subheader("Quelles compétences le marché demande-t-il ?")
    c1, c2 = st.columns([3, 2])
    sk = (B.groupby(["skill", "skill_family"]).agg(n=("offer_id", "nunique"),
          must=("requirement", lambda s: (s == "Indispensable").sum())).reset_index())
    sk["pct"] = 100 * sk["n"] / max(n, 1)
    top = sk.sort_values("n", ascending=False).head(20)
    fig = go.Figure()
    fig.add_bar(y=top["skill"], x=top["must"], orientation="h", name="Indispensable", marker_color=CAT[0],
                hovertemplate="%{y}<br>Indispensable dans %{x} offres<extra></extra>")
    fig.add_bar(y=top["skill"], x=top["n"] - top["must"], orientation="h", name="Souhaitée / mentionnée", marker_color=BLUE_SEQ[1],
                hovertemplate="%{y}<br>Souhaitée dans %{x} offres<extra></extra>")
    fig.update_layout(barmode="stack", bargap=0.35, title="Top 20 compétences (nombre d'offres)", yaxis=dict(autorange="reversed"))
    c1.plotly_chart(style(fig, h=560), use_container_width=True)

    famc = B.groupby("skill_family")["offer_id"].nunique().sort_values(ascending=False).reset_index(name="n")
    famc["pct"] = 100 * famc["n"] / max(n, 1)
    fig = px.bar(famc, x="pct", y="skill_family", orientation="h", title="Part des offres citant au moins une compétence de la famille",
                 text=famc["pct"].map(lambda v: f"{v:.0f} %"), color_discrete_sequence=[CAT[0]])
    fig.update_traces(textposition="outside", hovertemplate="%{y}<br>%{x:.0f} % des offres<extra></extra>")
    fig.update_layout(yaxis=dict(autorange="reversed", title=""), xaxis=dict(title="% des offres", range=[0, 110]), bargap=0.35)
    c2.plotly_chart(style(fig, h=560, legend=False), use_container_width=True)
    if show_table:
        st.dataframe(sk.sort_values("n", ascending=False), use_container_width=True, hide_index=True)

    # Compétences par famille de poste (heatmap)
    st.markdown("**Compétences clés par famille de poste** (% des offres de la famille)")
    key = ["SQL", "Power BI", "Python", "Excel", "Agile / Scrum", "Anglais", "IA / LLM", "Data Governance", "Data Quality", "ETL", "Azure", "GCP", "Tableau", "SAP"]
    m = (B[B["skill"].isin(key)].merge(O[["offer_id", "job_family"]], on="offer_id")
         .groupby(["job_family", "skill"])["offer_id"].nunique().unstack(fill_value=0))
    m = m.reindex(columns=[k for k in key if k in m.columns]).div(O["job_family"].value_counts(), axis=0).mul(100).round(0)
    m = m.loc[O["job_family"].value_counts().index.intersection(m.index)]
    fig = px.imshow(m, color_continuous_scale=BLUE_SEQ, text_auto=".0f", aspect="auto", zmin=0, zmax=100)
    fig.update_traces(hovertemplate="%{y} · %{x}<br>%{z:.0f} % des offres<extra></extra>")
    fig.update_layout(coloraxis_colorbar=dict(title="%"), xaxis_title="", yaxis_title="")
    st.plotly_chart(style(fig, h=380, legend=False), use_container_width=True)

# --------------------------------------------------------------------- Salaires
with tabs[1]:
    st.subheader("Combien paient les postes, et qui l'affiche ?")
    S = O[O["salary_mid"].notna()]
    n_tjm = int(O["tjm_max"].notna().sum())
    if n_tjm:
        st.caption(f"{n_tjm} offre(s) freelance exprimée(s) en TJM (jusqu'à {O['tjm_max'].max():.0f} €/jour) sont exclues des graphiques de salaire.")
    c1, c2 = st.columns([3, 2])
    order = O["job_family"].value_counts().index.tolist()
    if len(S):
        fig = px.box(S, x="salary_mid", y="job_family", points="all", category_orders={"job_family": order},
                     color_discrete_sequence=[CAT[0]], title="Distribution des salaires par famille (brut annuel, point médian de la fourchette)")
        fig.update_traces(marker=dict(size=8, opacity=0.7), hovertemplate="%{x:,.0f} €<extra></extra>", boxmean=False, line_width=2)
        fig.update_layout(xaxis_title="€ brut / an", yaxis_title="")
        c1.plotly_chart(style(fig, h=440, legend=False), use_container_width=True)
    else:
        c1.info("Aucune offre avec salaire dans la sélection.")
    tr = O.groupby("job_family").agg(n=("offer_id", "count"), with_sal=("salary_mid", lambda s: s.notna().sum())).reset_index()
    tr["pct"] = 100 * tr["with_sal"] / tr["n"]
    tr = tr.set_index("job_family").loc[order].reset_index()
    fig = px.bar(tr, x="pct", y="job_family", orientation="h", text=tr["pct"].map(lambda v: f"{v:.0f} %"),
                 title="Transparence salariale : % d'offres affichant un salaire", color_discrete_sequence=[CAT[1]])
    fig.update_traces(textposition="outside", hovertemplate="%{y}<br>%{x:.0f} % des offres<extra></extra>")
    fig.update_layout(yaxis=dict(autorange="reversed", title=""), xaxis=dict(title="% des offres", range=[0, 110]), bargap=0.35)
    c2.plotly_chart(style(fig, h=440, legend=False), use_container_width=True)
    if len(S):
        st.markdown("**Salaire médian par type d'entreprise**")
        ct = S.groupby("company_type")["salary_mid"].agg(["median", "count"]).reset_index().sort_values("median", ascending=False)
        fig = px.bar(ct, x="company_type", y="median", text=ct["median"].map(lambda v: f"{v/1000:.0f} k€"),
                     color_discrete_sequence=[CAT[0]], custom_data=["count"])
        fig.update_traces(textposition="outside", hovertemplate="%{x}<br>médiane %{y:,.0f} € · %{customdata[0]} offres<extra></extra>")
        fig.update_layout(xaxis_title="", yaxis_title="€ brut / an", bargap=0.45)
        st.plotly_chart(style(fig, h=320, legend=False), use_container_width=True)
    if show_table:
        st.dataframe(S[["title", "company", "job_family", "region", "salary_min", "salary_max", "salary_format"]].sort_values("salary_min", ascending=False),
                     use_container_width=True, hide_index=True)

# --------------------------------------------------------------------- Géographie
with tabs[2]:
    st.subheader("Où sont les postes, et peut-on télétravailler ?")
    c1, c2 = st.columns(2)
    g = O["region"].value_counts().reset_index()
    g.columns = ["region", "n"]
    fig = px.bar(g, x="n", y="region", orientation="h", text="n", title="Offres par région", color_discrete_sequence=[CAT[0]])
    fig.update_traces(textposition="outside", hovertemplate="%{y}<br>%{x} offres<extra></extra>")
    fig.update_layout(yaxis=dict(autorange="reversed", title=""), xaxis_title="offres", bargap=0.35)
    c1.plotly_chart(style(fig, h=420, legend=False), use_container_width=True)

    rp_order = ["Hybride", "Télétravail complet", "Présentiel", "Non précisé"]
    rp = O["remote_policy"].value_counts().reindex(rp_order, fill_value=0).reset_index()
    rp.columns = ["policy", "n"]
    rp["pct"] = 100 * rp["n"] / max(n, 1)
    fig = px.bar(rp, x="policy", y="pct", text=rp["pct"].map(lambda v: f"{v:.0f} %"), title="Politique de télétravail affichée",
                 color="policy", color_discrete_map=dict(zip(rp_order, [CAT[0], CAT[2], CAT[1], "#b5b3ad"])))
    fig.update_traces(textposition="outside", hovertemplate="%{x}<br>%{y:.0f} % des offres<extra></extra>")
    fig.update_layout(xaxis_title="", yaxis=dict(title="% des offres", range=[0, 100]), bargap=0.45, showlegend=False)
    c2.plotly_chart(style(fig, h=420, legend=False), use_container_width=True)

    idf = O[O["region"] == "Île-de-France"]
    if len(idf):
        d = idf["department"].value_counts().reset_index()
        d.columns = ["dept", "n"]
        d["dept"] = d["dept"].map({"75": "75 Paris", "92": "92 Hauts-de-Seine", "93": "93 Seine-Saint-Denis", "94": "94 Val-de-Marne",
                                   "77": "77 Seine-et-Marne", "78": "78 Yvelines", "91": "91 Essonne", "95": "95 Val-d'Oise"}).fillna(d["dept"])
        fig = px.bar(d, x="dept", y="n", text="n", title="Zoom Île-de-France : offres par département", color_discrete_sequence=[CAT[0]])
        fig.update_traces(textposition="outside", hovertemplate="%{x}<br>%{y} offres<extra></extra>")
        fig.update_layout(xaxis_title="", yaxis_title="offres", bargap=0.45)
        st.plotly_chart(style(fig, h=300, legend=False), use_container_width=True)
    if show_table:
        st.dataframe(O[["title", "company", "city", "department", "region", "remote_policy"]], use_container_width=True, hide_index=True)

# --------------------------------------------------------------------- Séniorité
with tabs[3]:
    st.subheader("Le marché junior existe-t-il ?")
    sen_order = ["Junior (0-2 ans)", "Confirmé (3-5 ans)", "Senior (5 ans et +)", "Non précisé"]
    sen_colors = dict(zip(sen_order, [CAT[2], CAT[0], CAT[1], "#b5b3ad"]))
    c1, c2 = st.columns([3, 2])
    s = (O.groupby(["job_family", "seniority"]).size().reset_index(name="n"))
    s["pct"] = 100 * s["n"] / s.groupby("job_family")["n"].transform("sum")
    fig = px.bar(s, y="job_family", x="pct", color="seniority", orientation="h", category_orders={"job_family": order, "seniority": sen_order},
                 color_discrete_map=sen_colors, title="Séniorité demandée par famille de poste (% des offres)")
    fig.update_traces(hovertemplate="%{y}<br>%{fullData.name} : %{x:.0f} %<extra></extra>", marker_line=dict(width=2, color="white"))
    fig.update_layout(barmode="stack", yaxis=dict(title="", categoryorder="array", categoryarray=order[::-1]), xaxis_title="% des offres", bargap=0.35, legend_title_text="")
    c1.plotly_chart(style(fig, h=440), use_container_width=True)

    yrs = O["min_years_experience"].dropna()
    if len(yrs):
        fig = px.histogram(yrs, nbins=12, title="Années d'expérience minimum exigées", color_discrete_sequence=[CAT[0]])
        fig.update_traces(hovertemplate="%{x} ans<br>%{y} offres<extra></extra>", marker_line=dict(width=2, color="white"))
        fig.update_layout(xaxis_title="années", yaxis_title="offres", showlegend=False, bargap=0.05)
        c2.plotly_chart(style(fig, h=440, legend=False), use_container_width=True)

    st.markdown("**Flux entrant : part des recommandations jugées « trop senior » par source**")
    ts = reco.groupby("source").agg(n=("recommendation_id", "count"), senior=("flag_senior", "sum"),
                                    rej_senior=("reject_reason", lambda s: (s == "Trop senior").sum())).reset_index()
    ts["pct"] = 100 * (ts["senior"] + ts["rej_senior"]).clip(upper=ts["n"]) / ts["n"]
    ts = ts[ts["n"] >= 3].sort_values("pct", ascending=False)
    fig = px.bar(ts, x="source", y="pct", text=ts["pct"].map(lambda v: f"{v:.0f} %"), color_discrete_sequence=[CAT[1]], custom_data=["n"])
    fig.update_traces(textposition="outside", hovertemplate="%{x}<br>%{y:.0f} % trop senior · %{customdata[0]} reçues<extra></extra>")
    fig.update_layout(xaxis_title="", yaxis=dict(title="% des offres reçues", range=[0, 100]), bargap=0.45)
    st.plotly_chart(style(fig, h=300, legend=False), use_container_width=True)
    if show_table:
        st.dataframe(s, use_container_width=True, hide_index=True)

# --------------------------------------------------------------------- Entonnoir
with tabs[4]:
    st.subheader("De l'offre reçue à l'entretien : où se perd le flux ?")
    stages = [
        ("Offres reçues (alertes + recherches)", len(reco)),
        ("Analysées en détail", len(offers)),
        ("Validées (IA + candidate)", int((offers["decision"] == "accepted").sum())),
        ("Candidatures envoyées", int(apps["is_applied"].sum())),
        ("Entretiens", int(apps["status"].isin(["entretien", "accepte", "offre"]).sum())),
    ]
    c1, c2 = st.columns([3, 2])
    fig = go.Figure(go.Funnel(y=[s[0] for s in stages], x=[s[1] for s in stages], textinfo="value+percent initial",
                              marker=dict(color=[BLUE_SEQ[4], BLUE_SEQ[3], BLUE_SEQ[2], BLUE_SEQ[2], BLUE_SEQ[1]], line=dict(width=2, color="white")),
                              connector=dict(visible=False), hovertemplate="%{y}<br>%{x} (%{percentInitial:.0%} du flux)<extra></extra>"))
    fig.update_layout(title="Entonnoir (tables : recommandations → offres → candidatures)")
    c1.plotly_chart(style(fig, h=440, legend=False), use_container_width=True)
    st.caption(f"Sur {len(reco)} offres reçues, {int(reco['status'].isin(['accepted','analyzed']).sum())} ont passé le tri rapide ; les offres analysées incluent aussi des imports manuels (favori « Envoyer à JobPilot ») qui ne passent pas par le flux reçu.")

    rr = reco[(reco["status"] == "rejected") & (reco["reject_reason"].fillna("") != "")]["reject_reason"].value_counts().reset_index()
    rr.columns = ["reason", "n"]
    rr["pct"] = 100 * rr["n"] / rr["n"].sum() if len(rr) else 0
    fig = px.bar(rr, x="pct", y="reason", orientation="h", text=rr["pct"].map(lambda v: f"{v:.0f} %"), title="Pourquoi une offre est écartée",
                 color_discrete_sequence=[CAT[1]])
    fig.update_traces(textposition="outside", hovertemplate="%{y}<br>%{x:.0f} % des rejets<extra></extra>")
    fig.update_layout(yaxis=dict(autorange="reversed", title=""), xaxis=dict(title="% des rejets", range=[0, 110]), bargap=0.35)
    c2.plotly_chart(style(fig, h=440, legend=False), use_container_width=True)

    c3, c4 = st.columns(2)
    sq = reco.groupby("source").agg(n=("recommendation_id", "count"), acc=("status", lambda s: (s == "accepted").sum())).reset_index()
    sq["rate"] = 100 * sq["acc"] / sq["n"]
    sq = sq[sq["n"] >= 3].sort_values("n", ascending=False)
    fig = go.Figure()
    fig.add_bar(x=sq["source"], y=sq["n"], name="Offres reçues", marker_color=BLUE_SEQ[1], hovertemplate="%{x}<br>%{y} reçues<extra></extra>")
    fig.add_bar(x=sq["source"], y=sq["acc"], name="Retenues", marker_color=CAT[0], hovertemplate="%{x}<br>%{y} retenues<extra></extra>")
    fig.update_layout(barmode="group", title="Volume et taux de rétention par source", xaxis_title="", yaxis_title="offres", bargap=0.3)
    c3.plotly_chart(style(fig, h=380), use_container_width=True)

    st_order = ["À postuler", "Postulé", "Entretien", "Refusé", "Abandonné", "Expirée"]
    stt = apps["status_label"].value_counts().reindex(st_order, fill_value=0).reset_index()
    stt.columns = ["status", "n"]
    fig = px.bar(stt, x="status", y="n", text="n", title="Statut des candidatures suivies", color_discrete_sequence=[CAT[0]])
    fig.update_traces(textposition="outside", hovertemplate="%{x}<br>%{y} candidatures<extra></extra>")
    fig.update_layout(xaxis_title="", yaxis_title="candidatures", bargap=0.45)
    c4.plotly_chart(style(fig, h=380, legend=False), use_container_width=True)

    # Rythme hebdo
    wk = offers.groupby(offers["collected_at"].dt.strftime("%G-S%V")).size().reset_index(name="offres")
    wk.columns = ["semaine", "offres"]
    rk = reco.groupby(reco["received_at"].dt.strftime("%G-S%V")).size().reset_index(name="reçues")
    rk.columns = ["semaine", "reçues"]
    wk = wk.merge(rk, on="semaine", how="outer").fillna(0).sort_values("semaine")
    fig = go.Figure()
    fig.add_scatter(x=wk["semaine"], y=wk["reçues"], mode="lines+markers", name="Offres reçues", line=dict(color=CAT[1], width=2), marker=dict(size=8))
    fig.add_scatter(x=wk["semaine"], y=wk["offres"], mode="lines+markers", name="Offres analysées", line=dict(color=CAT[0], width=2), marker=dict(size=8))
    fig.update_layout(title="Rythme hebdomadaire", xaxis_title="", yaxis_title="offres", hovermode="x unified")
    st.plotly_chart(style(fig, h=300), use_container_width=True)
    if show_table:
        st.dataframe(sq, use_container_width=True, hide_index=True)

# --------------------------------------------------------------------- Méthode
with tabs[5]:
    st.subheader("Méthode et limites")
    st.markdown(
        """
**Source.** Offres d'emploi collectées entre fin octobre et novembre 2026 via JobPilot (outil de suivi de candidatures que j'ai développé) :
alertes e-mail (LinkedIn, Indeed, HelloWork, France Travail, Adzuna, Glassdoor…), recherches et import manuel depuis les sites entreprises.
Chaque offre est analysée par un LLM qui en extrait une structure (compétences indispensables / souhaitées, salaire, séniorité, télétravail, secteur).

**Pipeline.** `src/clean.py` (pandas) : normalisation des salaires (K€, mensuel, fourchettes → brut annuel), de la séniorité (texte libre → 3 classes + années),
des lieux (code postal / ville → département → région), des contrats et des sources ; détection de 80 compétences canoniques par expressions régulières
sur les champs structurés ; export d'un **modèle en étoile** (3 tables de faits, 2 dimensions, 1 table de pont) chargé dans PostgreSQL (`sql/`) et consommé par Power BI et ce dashboard.

**Limites à garder en tête.**
- L'échantillon est **biaisé par mes recherches** : postes Data / BI / Business Analyst, surtout en Île-de-France, niveau junior à confirmé. Ce n'est pas le marché français complet.
- Les champs structurés sont produits par un LLM : les erreurs d'extraction (séniorité devinée, salaire absent) sont corrigées en partie par le pipeline, pas totalement.
- Les offres Indeed / Glassdoor n'ont souvent que l'extrait de l'annonce : moins de compétences détectées.
- Les salaires ne sont affichés que dans une minorité d'offres ; les médianes sont indicatives.
        """
    )
    st.dataframe(T["dim_skill"], use_container_width=True, hide_index=True)
