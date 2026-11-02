"""
Moteur de recommandations : transforme les indicateurs en actions concrètes, par agence.
Les règles sont volontairement explicites (système expert) pour rester explicables en soutenance.
"""
import numpy as np
import pandas as pd

ORDRE = {"Haute": 0, "Moyenne": 1, "Info": 2}

SEUIL_BAISSE = -10.0       # % de variation 3 mois vs 3 mois précédents
SEUIL_HAUSSE = 10.0
SEUIL_OBJECTIF = 0.90      # CA < 90 % de l'objectif
SEUIL_CONCENTRATION = 0.35 # un produit pèse plus de 35 % du CA
SEUIL_INACTIFS = 0.30      # plus de 30 % des clients RÉCURRENTS devenus inactifs
JOURS_INACTIF = 90
MIN_ACHATS_RECURRENT = 2   # un client récurrent a acheté au moins 2 fois


def construire_recommandations(pivot: pd.DataFrame, kpi: pd.DataFrame, produits: pd.DataFrame,
                               clients: pd.DataFrame, agents: pd.DataFrame) -> list[dict]:
    reco = []

    def ajouter(agence, priorite, theme, constat, action):
        reco.append(dict(agence=agence, priorite=priorite, theme=theme, constat=constat, action=action))

    # 1. Tendance du chiffre d'affaires
    for agence in pivot.columns:
        y = pivot[agence].astype(float).tolist()
        if len(y) < 6:
            continue
        recent, precedent = np.mean(y[-3:]), np.mean(y[-6:-3])
        var = (recent - precedent) / precedent * 100 if precedent else 0.0
        if var <= SEUIL_BAISSE:
            ajouter(agence, "Haute", "Tendance", f"CA en baisse de {abs(var):.0f} % sur les 3 derniers mois.",
                    "Identifier les clients perdus et lancer une campagne de relance ciblée ; revoir l'offre commerciale.")
        elif var >= SEUIL_HAUSSE:
            ajouter(agence, "Info", "Tendance", f"CA en hausse de {var:.0f} % sur les 3 derniers mois.",
                    "Capitaliser : repérer les produits moteurs, sécuriser les stocks et partager les bonnes pratiques.")

    # 2. Atteinte de l'objectif
    for _, r in kpi.iterrows():
        if r["objectif"] and r["ca"] < SEUIL_OBJECTIF * r["objectif"]:
            taux = r["ca"] / r["objectif"] * 100
            manque = (r["objectif"] - r["ca"]) / 1e6
            prio = "Haute" if taux < 75 else "Moyenne"
            ajouter(r["agence"], prio, "Objectif",
                    f"Objectif atteint à {taux:.0f} % ; il manque {manque:,.0f} M Ar.".replace(",", " "),
                    "Définir un plan d'action chiffré avec le responsable d'agence et suivre l'avancement chaque semaine.")

    # 3. Concentration sur un produit
    if not produits.empty:
        for agence, g in produits.groupby("agence"):
            total = g["ca"].sum()
            if not total:
                continue
            top = g.sort_values("ca", ascending=False).iloc[0]
            part = top["ca"] / total
            if part > SEUIL_CONCENTRATION:
                ajouter(agence, "Moyenne", "Produits",
                        f"{part*100:.0f} % du CA repose sur un seul produit ({top['produit']}).",
                        "Réduire la dépendance : pousser des produits complémentaires et diversifier le portefeuille.")

    # 4. Clients récurrents devenus inactifs (les clients à achat unique ne comptent pas)
    if not clients.empty:
        clients = clients.copy()
        clients["derniere"] = pd.to_datetime(clients["derniere"])
        ref = clients["derniere"].max()
        recurrents = clients[clients["frequence"] >= MIN_ACHATS_RECURRENT]
        for agence, g in recurrents.groupby("agence"):
            if len(g) < 5:
                continue
            inactifs = ((ref - g["derniere"]).dt.days > JOURS_INACTIF).mean()
            if inactifs > SEUIL_INACTIFS:
                ajouter(agence, "Moyenne", "Clients",
                        f"{inactifs*100:.0f} % des clients récurrents n'ont rien acheté depuis plus de {JOURS_INACTIF} jours.",
                        "Planifier des appels ou offres de réactivation pour ces clients fidèles devenus dormants.")

    # 5. Agents en retrait
    if not agents.empty:
        for agence, g in agents.groupby("agence"):
            g = g.copy()
            fixes = g[g["objectif"] > 0]
            if len(fixes) > 0:
                for _, a in fixes.iterrows():
                    taux = a["ca"] / a["objectif"] * 100
                    if taux < 70:
                        ajouter(agence, "Moyenne", "Agents",
                                f"{a['agent']} est à {taux:.0f} % de son objectif.",
                                "Prévoir un accompagnement individuel (coaching, revue du portefeuille clients).")
            elif len(g) >= 3:
                mediane = g["ca"].median()
                for _, a in g.iterrows():
                    if mediane and a["ca"] < 0.5 * mediane:
                        ajouter(agence, "Moyenne", "Agents",
                                f"{a['agent']} réalise moins de la moitié du CA médian de l'agence.",
                                "Vérifier la charge et le portefeuille de cet agent ; définir des objectifs individuels.")

    reco.sort(key=lambda r: (ORDRE[r["priorite"]], r["agence"]))
    return reco


def charger_recommandations() -> list[dict]:
    from app.db import engine
    from ml.prevision import historique_mensuel_par_agence
    pivot = historique_mensuel_par_agence()
    kpi = pd.read_sql("""SELECT da.agence, da.objectif, COALESCE(SUM(f.montant),0) AS ca
        FROM dim_agence da LEFT JOIN fait_vente f ON f.id_agence = da.id_agence
        GROUP BY da.agence, da.objectif""", engine)
    produits = pd.read_sql("""SELECT da.agence, dp.produit, SUM(f.montant) AS ca FROM fait_vente f
        JOIN dim_agence da ON da.id_agence = f.id_agence
        JOIN dim_produit dp ON dp.id_produit = f.id_produit GROUP BY da.agence, dp.produit""", engine)
    clients = pd.read_sql("""SELECT da.agence, dc.client, MAX(dd.date) AS derniere, COUNT(*) AS frequence FROM fait_vente f
        JOIN dim_agence da ON da.id_agence = f.id_agence
        JOIN dim_client dc ON dc.id_client = f.id_client
        JOIN dim_date dd ON dd.id_temps = f.id_temps GROUP BY da.agence, dc.client""", engine)
    agents = pd.read_sql("""SELECT da.agence, dagt.agent, dagt.objectif, COALESCE(SUM(f.montant),0) AS ca
        FROM dim_agent dagt JOIN dim_agence da ON da.id_agence = dagt.id_agence
        LEFT JOIN fait_vente f ON f.id_agent = dagt.id_agent
        GROUP BY da.agence, dagt.agent, dagt.objectif""", engine)
    return construire_recommandations(pivot, kpi, produits, clients, agents)
