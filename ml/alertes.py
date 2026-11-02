import numpy as np
import pandas as pd
from app.db import engine
from ml.prevision import prevoir, historique_mensuel_par_agence

def generer_alertes() -> list[dict]:
    alertes = []
    piv = historique_mensuel_par_agence()

    for agence in piv.columns:
        y = piv[agence].tolist()
        if len(y) < 6:
            continue
        recent = np.mean(y[-3:])
        precedent = np.mean(y[-6:-3])
        variation = (recent - precedent) / precedent * 100 if precedent else 0

        if variation <= -10:
            alertes.append({"niveau": "risque",
                            "texte": f"{agence} : CA en baisse de {abs(variation):.0f} % "
                                    f"sur les 3 derniers mois vs les 3 précédents."})
        elif variation >= 10:
            alertes.append({"niveau": "positif",
                            "texte": f"{agence} : CA en hausse de {variation:.0f} % "
                                    f"sur les 3 derniers mois."})

    kpi = pd.read_sql("""
        SELECT da.agence, da.objectif, COALESCE(SUM(f.montant),0) AS ca
        FROM dim_agence da LEFT JOIN fait_vente f ON f.id_agence = da.id_agence
        GROUP BY da.agence, da.objectif
    """, engine)

    for _, r in kpi.iterrows():
        if r["objectif"] and r["ca"] < 0.9 * r["objectif"]:
            ecart = (r["ca"] - r["objectif"]) / r["objectif"] * 100
            alertes.append({"niveau": "risque",
                            "texte": f"{r['agence']} : objectif non atteint ({ecart:.0f} %)."})
    return alertes