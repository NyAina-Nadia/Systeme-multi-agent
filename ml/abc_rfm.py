"""Analyse ABC (Pareto) des produits et segmentation RFM des clients."""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


# ---------------------------------------------------------------- ABC
def classer_abc(df: pd.DataFrame, seuil_a=0.80, seuil_b=0.95) -> pd.DataFrame:
    """df : colonnes 'produit' et 'ca'. Retourne le tableau trié avec part, cumul et classe A/B/C.
    Un produit est de classe A tant que le cumul AVANT lui est < 80 % (celui qui franchit le seuil reste A)."""
    out = df.groupby("produit", as_index=False)["ca"].sum().sort_values("ca", ascending=False)
    out = out.reset_index(drop=True)
    total = out["ca"].sum()
    out["part"] = out["ca"] / total if total else 0.0
    out["cumul"] = out["part"].cumsum()
    avant = out["cumul"] - out["part"]
    out["classe"] = np.where(avant < seuil_a, "A", np.where(avant < seuil_b, "B", "C"))
    return out


def analyse_abc() -> pd.DataFrame:
    from app.db import engine
    df = pd.read_sql("""SELECT dp.produit, SUM(f.montant) AS ca FROM fait_vente f
        JOIN dim_produit dp ON dp.id_produit = f.id_produit GROUP BY dp.produit""", engine)
    return classer_abc(df)


# ---------------------------------------------------------------- RFM
SEUIL_FREQUENCE_EXPLOITABLE = 0.05   # au moins 5 % de clients ayant acheté 2 fois ou plus


def calculer_rfm(df: pd.DataFrame, k: int = 3, date_reference=None) -> pd.DataFrame:
    """df : colonnes 'client', 'derniere' (dernier achat), 'frequence', 'montant'.
    Ajoute 'recence' (jours), 'groupe' (numéro K-means) et 'segment' (libellé métier).
    Si presque aucun client n'a acheté plusieurs fois, la fréquence n'apporte rien : elle est
    écartée et le résultat porte l'attribut df.attrs['frequence_exploitable'] = False."""
    df = df.copy()
    df["derniere"] = pd.to_datetime(df["derniere"])
    ref = pd.to_datetime(date_reference) if date_reference is not None else df["derniere"].max()
    df["recence"] = (ref - df["derniere"]).dt.days
    exploitable = bool((df["frequence"] >= 2).mean() >= SEUIL_FREQUENCE_EXPLOITABLE)
    k = max(1, min(k, len(df)))
    if len(df) < 3 or k == 1:
        df["groupe"] = 0
        df["segment"] = "Clients réguliers"
        df.attrs["frequence_exploitable"] = exploitable
        return df

    colonnes = ["recence", "frequence", "montant"] if exploitable else ["recence", "montant"]
    # échelle log : évite qu'une poignée de gros clients écrase tous les autres groupes
    X = StandardScaler().fit_transform(np.log1p(df[colonnes]))
    df["groupe"] = KMeans(k, n_init=10, random_state=42).fit_predict(X)

    z = pd.DataFrame(X, columns=colonnes, index=df.index)
    score = z["montant"] - z["recence"]
    if exploitable:
        score = score + z["frequence"]
    df["_score"] = score
    classement = df.groupby("groupe")["_score"].mean().sort_values().index.tolist()
    libelles = (["Clients à relancer", "Clients réguliers", "Clients fidèles"] if exploitable
                else ["Petits acheteurs", "Acheteurs moyens", "Gros acheteurs"])
    noms = {}
    for rang, g in enumerate(classement):
        noms[g] = libelles[0] if rang == 0 else libelles[2] if rang == len(classement) - 1 else libelles[1]
    df["segment"] = df["groupe"].map(noms)
    df = df.drop(columns="_score")
    df.attrs["frequence_exploitable"] = exploitable
    return df


def segmentation_rfm(k: int = 3) -> pd.DataFrame:
    from app.db import engine
    df = pd.read_sql("""SELECT dc.client, MAX(dd.date) AS derniere, COUNT(*) AS frequence,
        SUM(f.montant) AS montant FROM fait_vente f
        JOIN dim_client dc ON dc.id_client = f.id_client
        JOIN dim_date dd ON dd.id_temps = f.id_temps GROUP BY dc.client""", engine)
    if df.empty:
        return df
    return calculer_rfm(df, k)
