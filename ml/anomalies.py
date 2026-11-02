"""
Détection des transactions atypiques : Isolation Forest + règles de contrôle métier.

Une anomalie statistique n'est pas forcément un problème : une très grosse vente d'un produit cher,
au prix du catalogue et pour une quantité courante, est inhabituelle sans être suspecte.
Les règles métier servent donc à CONFIRMER (règles aggravantes) ou à RELATIVISER (justification
par le catalogue) le résultat du modèle, et chaque ligne est expliquée par ses motifs.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

REQUETE = """
    SELECT f.id_vente, da.agence, dp.produit, f.quantite, f.prix_unitaire, f.montant,
           dc.client, dd.date
    FROM fait_vente f
    JOIN dim_agence da ON da.id_agence = f.id_agence
    JOIN dim_produit dp ON dp.id_produit = f.id_produit
    JOIN dim_client dc ON dc.id_client = f.id_client
    JOIN dim_date dd ON dd.id_temps = f.id_temps
"""

# Seuils des règles (modifiables)
ECART_PRIX_AGGRAVANT = 0.20     # prix unitaire à plus de ±20 % de la médiane du produit
ECART_PRIX_CONFORME = 0.05      # en dessous de ±5 % : prix conforme au catalogue
TOLERANCE_MONTANT = 0.01        # |montant - quantité x prix| > 1 % du montant
MIN_OBS_PRODUIT = 5             # nombre minimal de ventes d'un produit pour juger son prix
RANG = {"Élevé": 0, "Moyen": 1, "Faible": 2}


def appliquer_regles(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute les colonnes : regles (liste de motifs aggravants), justifiee (bool). Logique pure."""
    df = df.copy()
    pu = df["prix_unitaire"].astype(float)
    montant = df["montant"].astype(float)
    qte = df["quantite"].astype(float)

    g = df.groupby("produit")
    med_prix = g["prix_unitaire"].transform("median").astype(float)
    nb_prod = g["prix_unitaire"].transform("count")
    med_qte = g["quantite"].transform("median").astype(float)
    p95_qte = g["quantite"].transform(lambda s: s.quantile(0.95)).astype(float)
    p99_qte = g["quantite"].transform(lambda s: s.quantile(0.99)).astype(float)
    ecart_prix = ((pu - med_prix) / med_prix.replace(0, np.nan)).fillna(0.0)

    q1 = df.groupby("agence")["montant"].transform(lambda s: s.quantile(0.25)).astype(float)
    q3 = df.groupby("agence")["montant"].transform(lambda s: s.quantile(0.75)).astype(float)
    seuil_extreme = q3 + 3 * (q3 - q1)
    p90 = montant.quantile(0.90)
    anonyme = df["client"].astype(str).str.strip().str.lower().isin(["client anonyme", "anonyme", ""])

    incoherence = ((montant - qte * pu).abs() / montant.replace(0, np.nan)).fillna(0.0)

    regles = [[] for _ in range(len(df))]
    def ajouter(masque, texte_fn):
        for i in np.flatnonzero(masque.to_numpy()):
            regles[i].append(texte_fn(i))

    ajouter((ecart_prix.abs() > ECART_PRIX_AGGRAVANT) & (nb_prod >= MIN_OBS_PRODUIT),
            lambda i: f"Prix unitaire à {ecart_prix.iloc[i]*100:+.0f} % de la médiane du produit")
    ajouter(qte > np.maximum(p99_qte, 2 * med_qte),
            lambda i: f"Quantité ({int(qte.iloc[i])}) très supérieure à l'usage du produit")
    ajouter(incoherence > TOLERANCE_MONTANT,
            lambda i: "Montant différent de quantité × prix unitaire")
    ajouter(anonyme & (montant >= p90),
            lambda i: "Client anonyme pour un montant élevé")
    ajouter(montant > seuil_extreme,
            lambda i: "Montant extrême pour l'agence (> Q3 + 3 × IQR)")

    df["regles"] = regles
    df["justifiee"] = ((ecart_prix.abs() <= ECART_PRIX_CONFORME) & (incoherence <= TOLERANCE_MONTANT)
                       & (qte <= p95_qte) & (nb_prod >= MIN_OBS_PRODUIT)).to_numpy()
    return df


def classer(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute niveau et motifs à partir de anomalie_stat, regles et justifiee. Logique pure."""
    niveaux, motifs = [], []
    for stat, regles, just in zip(df["anomalie_stat"], df["regles"], df["justifiee"]):
        m = list(regles)
        if stat and regles:
            niveau = "Élevé"
        elif len(regles) >= 2:
            niveau = "Élevé"
        elif len(regles) == 1:
            niveau = "Moyen"
        elif stat and just:
            niveau = "Faible"
            m.append("Justifiée : prix du catalogue et quantité usuelle (grosse vente, non suspecte)")
        elif stat:
            niveau = "Moyen"
            m.append("Atypique statistiquement, sans explication par le catalogue")
        else:
            niveau = None
        if stat and niveau in ("Élevé", "Moyen") and regles:
            m.insert(0, "Confirmée par le modèle statistique")
        niveaux.append(niveau)
        motifs.append(" ; ".join(m))
    df = df.copy()
    df["niveau"], df["motifs"] = niveaux, motifs
    return df


def analyser(df: pd.DataFrame, contamination: float = 0.015) -> pd.DataFrame:
    """Chaîne complète sur un DataFrame de ventes (testable sans base de données)."""
    df = df.reset_index(drop=True).copy()
    if len(df) < 20:
        return df.iloc[0:0].assign(score=[], niveau=[], motifs=[], ratio=[])
    df["ratio"] = df["montant"] / df.groupby("agence")["montant"].transform("median")
    X = df[["quantite", "montant", "ratio"]]
    modele = IsolationForest(contamination=contamination, random_state=42).fit(X)
    df["score"] = -modele.score_samples(X)
    df["anomalie_stat"] = modele.predict(X) == -1
    df = classer(appliquer_regles(df))
    return df[df["niveau"].notna()]


def detecter_anomalies(contamination: float = 0.015, top_n: int = 20, inclure_faibles: bool = True) -> pd.DataFrame:
    """Anomalies triées par niveau puis par score. inclure_faibles=False ne garde que Élevé et Moyen."""
    from app.db import engine
    brut = pd.read_sql(REQUETE, engine)
    res = analyser(brut, contamination)
    if res.empty:
        return res.reindex(columns=["agence", "produit", "quantite", "montant", "ratio", "score", "niveau", "motifs"])
    if not inclure_faibles:
        res = res[res["niveau"] != "Faible"]
    res = res.assign(_r=res["niveau"].map(RANG)).sort_values(["_r", "score"], ascending=[True, False])
    return res.head(top_n)[["agence", "produit", "quantite", "montant", "ratio", "score", "niveau", "motifs"]]
