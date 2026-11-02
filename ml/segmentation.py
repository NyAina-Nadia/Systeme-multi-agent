"""
Segmentation des agents par K-means, sur des variables enrichies :
CA, nombre de ventes, panier moyen, clients distincts, produits distincts et régularité mensuelle.
Chaque agent est identifié par (agent, agence) : un même nom peut exister dans plusieurs agences.
"""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

REQUETE = """
    SELECT dagt.id_agent, dagt.agent, da.agence, COALESCE(dagt.objectif, 0) AS objectif,
           SUM(f.montant) AS ca, COUNT(*) AS n,
           COUNT(DISTINCT f.id_client) AS clients, COUNT(DISTINCT f.id_produit) AS produits
    FROM fait_vente f
    JOIN dim_agent dagt ON dagt.id_agent = f.id_agent
    JOIN dim_agence da ON da.id_agence = f.id_agence
    GROUP BY dagt.id_agent, dagt.agent, da.agence, dagt.objectif
"""
REQUETE_MENSUEL = """
    SELECT f.id_agent, dd.annee, dd.mois, SUM(f.montant) AS ca
    FROM fait_vente f JOIN dim_date dd ON dd.id_temps = f.id_temps
    GROUP BY f.id_agent, dd.annee, dd.mois
"""
VARIABLES = ["ca", "n", "panier", "clients", "produits", "irregularite"]


def segmenter_depuis(ag: pd.DataFrame, mensuel: pd.DataFrame = None, nb_groupes: int = 3) -> pd.DataFrame:
    """Logique pure. ag : id_agent, agent, agence, ca, n, clients, produits (+ objectif).
    mensuel : id_agent, annee, mois, ca (pour mesurer la régularité)."""
    g = ag.copy()
    g["ca"] = g["ca"].astype(float)
    g["panier"] = g["ca"] / g["n"]
    g["etiquette"] = g["agent"].astype(str) + " (" + g["agence"].astype(str) + ")"
    if mensuel is not None and len(mensuel):
        m = mensuel.groupby("id_agent")["ca"].agg(["mean", "std"]).fillna(0.0)
        cv = (m["std"] / m["mean"].replace(0, np.nan)).fillna(0.0)
        g["irregularite"] = g["id_agent"].map(cv).fillna(0.0)
    else:
        g["irregularite"] = 0.0
    if "objectif" in g:
        g["atteinte"] = np.where(g["objectif"].astype(float) > 0, g["ca"] / g["objectif"].astype(float) * 100, np.nan)
    if len(g) < nb_groupes:
        return g
    X = StandardScaler().fit_transform(g[VARIABLES])
    g["cluster"] = KMeans(nb_groupes, n_init=10, random_state=42).fit_predict(X)
    ordre = g.groupby("cluster")["ca"].mean().sort_values().index.tolist()      # groupes nommés par CA moyen croissant
    noms = {ordre[0]: "À accompagner", ordre[-1]: "Performants"}
    if len(ordre) == 3:
        noms[ordre[1]] = "Réguliers"
    g["segment"] = g["cluster"].map(noms)
    return g


def segmenter_agents(nb_groupes: int = 3) -> pd.DataFrame:
    from app.db import engine
    ag = pd.read_sql(REQUETE, engine)
    if ag.empty:
        return ag
    res = segmenter_depuis(ag, pd.read_sql(REQUETE_MENSUEL, engine), nb_groupes)
    if "segment" not in res:
        return res
    res = res.drop(columns=["agent"]).rename(columns={"etiquette": "agent"})
    cols = ["agent", "agence", "ca", "n", "panier", "clients", "produits", "irregularite", "segment"]
    return res[cols + (["atteinte"] if "atteinte" in res else [])]
