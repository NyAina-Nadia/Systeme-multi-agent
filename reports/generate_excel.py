import pandas as pd
from app.db import engine
from ml.anomalies import detecter_anomalies
from ml.segmentation import segmenter_agents

def generer_export_excel(chemin_sortie: str = "export_performance.xlsx"):
    kpi = pd.read_sql("""
        SELECT da.agence, COALESCE(SUM(f.montant),0) AS ca, COUNT(f.id_vente) AS nb_ventes
        FROM dim_agence da LEFT JOIN fait_vente f ON f.id_agence = da.id_agence
        GROUP BY da.agence ORDER BY ca DESC
    """, engine)
    anomalies = detecter_anomalies(top_n=20)
    segments = segmenter_agents()

    with pd.ExcelWriter(chemin_sortie, engine="openpyxl") as writer:
        kpi.to_excel(writer, sheet_name="KPI par agence", index=False)
        anomalies.to_excel(writer, sheet_name="Anomalies", index=False)
        segments.to_excel(writer, sheet_name="Segmentation agents", index=False)
    return chemin_sortie

if __name__ == "__main__":
    chemin = generer_export_excel()
    print("Export généré :", chemin)    

# ---------------------------------------------------------------------------------------------
# Export PERSONNALISABLE : l'utilisateur choisit les feuilles, l'agence et la période
# ---------------------------------------------------------------------------------------------
SECTIONS = {
    "kpi": "KPI par agence",
    "mensuel": "Évolution mensuelle",
    "produits": "Ventes par produit",
    "agents": "Agents et objectifs",
    "anomalies": "Anomalies",
    "segmentation": "Segmentation agents",
    "recommandations": "Recommandations",
    "evaluation": "Suivi des prévisions",
}


def _filtre_sql(id_agence=None, date_debut=None, date_fin=None):
    conds, params = [], {}
    if id_agence:
        conds.append("f.id_agence = :a"); params["a"] = int(id_agence)
    if date_debut:
        conds.append("dd.date >= :d1"); params["d1"] = date_debut
    if date_fin:
        conds.append("dd.date <= :d2"); params["d2"] = date_fin
    return ("WHERE " + " AND ".join(conds)) if conds else "", params


def construire_feuilles(sections, id_agence=None, date_debut=None, date_fin=None) -> dict:
    """Retourne {nom de feuille: DataFrame} pour les sections demandées."""
    from sqlalchemy import text
    where, params = _filtre_sql(id_agence, date_debut, date_fin)
    base = "FROM fait_vente f JOIN dim_date dd ON dd.id_temps = f.id_temps"
    nom_agence = None
    if id_agence:
        nom_agence = pd.read_sql(text("SELECT agence FROM dim_agence WHERE id_agence = :a"), engine,
                                 params={"a": int(id_agence)}).iloc[0]["agence"]
    feuilles = {}

    if "kpi" in sections:
        feuilles[SECTIONS["kpi"]] = pd.read_sql(text(f"""
            SELECT da.agence, COALESCE(da.objectif, 0) AS objectif, SUM(f.montant) AS ca, COUNT(*) AS nb_ventes,
                   SUM(f.montant) / COUNT(*) AS panier_moyen
            {base} JOIN dim_agence da ON da.id_agence = f.id_agence {where}
            GROUP BY da.agence, da.objectif ORDER BY ca DESC"""), engine, params=params)
    if "mensuel" in sections:
        feuilles[SECTIONS["mensuel"]] = pd.read_sql(text(f"""
            SELECT dd.annee, dd.mois, da.agence, SUM(f.montant) AS ca, COUNT(*) AS nb_ventes
            {base} JOIN dim_agence da ON da.id_agence = f.id_agence {where}
            GROUP BY dd.annee, dd.mois, da.agence ORDER BY dd.annee, dd.mois, da.agence"""), engine, params=params)
    if "produits" in sections:
        feuilles[SECTIONS["produits"]] = pd.read_sql(text(f"""
            SELECT dp.categorie, dp.produit, SUM(f.quantite) AS quantite, SUM(f.montant) AS ca
            {base} JOIN dim_produit dp ON dp.id_produit = f.id_produit {where}
            GROUP BY dp.categorie, dp.produit ORDER BY ca DESC"""), engine, params=params)
    if "agents" in sections:
        df = pd.read_sql(text(f"""
            SELECT da.agence, dagt.agent, COALESCE(dagt.objectif, 0) AS objectif,
                   SUM(f.montant) AS ca, COUNT(*) AS nb_ventes
            {base} JOIN dim_agent dagt ON dagt.id_agent = f.id_agent
            JOIN dim_agence da ON da.id_agence = f.id_agence {where}
            GROUP BY da.agence, dagt.agent, dagt.objectif ORDER BY ca DESC"""), engine, params=params)
        df["atteinte_%"] = (df["ca"] / df["objectif"].where(df["objectif"] > 0) * 100).round(1)
        feuilles[SECTIONS["agents"]] = df
    if "anomalies" in sections:
        df = detecter_anomalies(top_n=500)
        feuilles[SECTIONS["anomalies"]] = df[df["agence"] == nom_agence] if nom_agence else df
    if "segmentation" in sections:
        df = segmenter_agents()
        feuilles[SECTIONS["segmentation"]] = df[df["agence"] == nom_agence] if nom_agence and "agence" in df else df
    if "recommandations" in sections:
        from ml.recommandations import charger_recommandations
        df = pd.DataFrame(charger_recommandations())
        feuilles[SECTIONS["recommandations"]] = df[df["agence"] == nom_agence] if nom_agence and not df.empty else df
    if "evaluation" in sections:
        from ml.backtest import diagnostic
        from ml.prevision import historique_mensuel_par_agence
        from ml.series import serie_agence
        piv, lignes = historique_mensuel_par_agence(), []
        for agence in (piv.columns if len(piv) else []):
            if nom_agence and agence != nom_agence:
                continue
            _, y = serie_agence(piv, agence)
            if len(y) < 7:
                continue
            d = diagnostic(y)
            lignes.append({"agence": agence, "modele_retenu": d["retenu"], "meilleur_global": d["meilleur_global"],
                           "derive": None if d["derive"] is None else round(d["derive"], 2),
                           "recommandation": d["recommandation"]})
        feuilles[SECTIONS["evaluation"]] = pd.DataFrame(lignes)
    return feuilles


def generer_export_personnalise(chemin_sortie, sections, id_agence=None, date_debut=None, date_fin=None):
    """Écrit un classeur Excel contenant uniquement les sections demandées (+ une feuille Paramètres)."""
    import datetime as dt
    feuilles = construire_feuilles(sections, id_agence, date_debut, date_fin)
    if not feuilles:
        raise ValueError("Choisissez au moins une section à exporter.")
    parametres = pd.DataFrame({
        "Paramètre": ["Date de l'export", "Agence", "Période", "Sections"],
        "Valeur": [dt.datetime.now().strftime("%d/%m/%Y %H:%M"),
                   "Toutes" if not id_agence else f"id {id_agence}",
                   f"{date_debut or 'début'} → {date_fin or 'fin'}",
                   ", ".join(feuilles)]})
    with pd.ExcelWriter(chemin_sortie, engine="openpyxl") as w:
        parametres.to_excel(w, sheet_name="Paramètres", index=False)
        for nom, df in feuilles.items():
            df.to_excel(w, sheet_name=nom[:31], index=False)
        for ws in w.book.worksheets:                       # largeur de colonnes lisible
            for col in ws.columns:
                largeur = max(len(str(c.value)) if c.value is not None else 0 for c in col)
                ws.column_dimensions[col[0].column_letter].width = min(60, max(12, largeur + 2))
    return chemin_sortie
