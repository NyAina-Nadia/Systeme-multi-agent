"""
Normalisation d'un fichier de ventes quelconque vers le schéma cible.
Ce module ne touche PAS à la base de données : il est donc testable seul.
"""
from pathlib import Path
import pandas as pd

SCHEMA_CIBLE = ["date", "produit", "categorie", "quantite",
                "prix_unitaire", "montant", "client", "commercial", "agence"]

# Colonnes que le fichier source DOIT fournir (montant ou prix_unitaire suffit pour l'autre)
OBLIGATOIRES = ["date", "produit", "quantite", "client"]

LIBELLES = {
    "date": "Date de la vente",
    "produit": "Produit",
    "categorie": "Catégorie (facultatif)",
    "quantite": "Quantité",
    "prix_unitaire": "Prix unitaire (facultatif si montant)",
    "montant": "Montant (facultatif si prix unitaire)",
    "client": "Client",
    "commercial": "Commercial (facultatif)",
}


def clean_text(s):
    if pd.isna(s):
        return s
    return " ".join(str(s).strip().split()).title() if isinstance(s, str) else s


def _en_nombre(serie: pd.Series) -> pd.Series:
    """Convertit '1 850,5' / '1850,5' / 1850.5 en nombre."""
    txt = (serie.astype(str)
           .str.replace("\u202f", "", regex=False)
           .str.replace("\xa0", "", regex=False)
           .str.replace(" ", "", regex=False)
           .str.replace(",", ".", regex=False))
    return pd.to_numeric(txt, errors="coerce")


def lire_fichier(chemin, sep=None, feuille=None) -> pd.DataFrame:
    """Lit un CSV (séparateur détecté si sep=None) ou un Excel."""
    chemin = Path(chemin)
    if chemin.suffix.lower() in (".xlsx", ".xlsm", ".xls"):
        return pd.read_excel(chemin, sheet_name=feuille or 0)
    return pd.read_csv(chemin, sep=sep or None, engine="python", encoding="utf-8-sig")


def normaliser(df, mapping: dict, agence: str,
               format_date: str | None = None, multiplicateur: float = 1.0):
    """
    mapping : {colonne_cible: colonne_du_fichier_source}  (None = absente)
    multiplicateur : 1000 si le fichier est en milliers d'Ariary (kAr).
    Retourne (DataFrame au schéma cible, dict de rapport qualité).
    """
    manquantes = [c for c in OBLIGATOIRES if not mapping.get(c)]
    if manquantes:
        raise ValueError("Colonnes obligatoires non associées : " + ", ".join(manquantes))
    if not mapping.get("montant") and not mapping.get("prix_unitaire"):
        raise ValueError("Associez au moins « montant » ou « prix_unitaire ».")
    for cible, src in mapping.items():
        if src and src not in df.columns:
            raise ValueError(f"Colonne « {src} » introuvable dans le fichier.")

    out = pd.DataFrame({cible: df[src] for cible, src in mapping.items() if src})
    n_lues = len(out)

    out["date"] = pd.to_datetime(out["date"], format=format_date or None,
                                 dayfirst=True, errors="coerce")
    out["quantite"] = _en_nombre(out["quantite"])

    if "prix_unitaire" in out:
        out["prix_unitaire"] = _en_nombre(out["prix_unitaire"]) * multiplicateur
    if "montant" in out:
        out["montant"] = _en_nombre(out["montant"]) * multiplicateur

    if "montant" not in out:
        out["montant"] = out["quantite"] * out["prix_unitaire"]
    else:
        if "prix_unitaire" in out:   # montant manquant -> quantité x prix
            out["montant"] = out["montant"].fillna(out["quantite"] * out["prix_unitaire"])
    if "prix_unitaire" not in out:
        out["prix_unitaire"] = out["montant"] / out["quantite"]
    else:
        out["prix_unitaire"] = out["prix_unitaire"].fillna(out["montant"] / out["quantite"])

    if "categorie" not in out:
        out["categorie"] = "Non classé"
    if "commercial" not in out:
        out["commercial"] = "Non renseigné"

    for col in ("produit", "categorie", "client"):
        out[col] = out[col].apply(clean_text)
    out["commercial"] = out["commercial"].apply(clean_text).fillna("Non renseigné")
    out["categorie"] = out["categorie"].fillna("Non classé")
    out["agence"] = agence.strip()

    out = out[SCHEMA_CIBLE]
    avant = len(out)
    out = out.dropna(subset=["date", "produit", "quantite", "montant", "client"])
    out = out[(out["quantite"] > 0) & (out["montant"] >= 0)]
    apres_filtre = len(out)
    out = out.drop_duplicates().reset_index(drop=True)

    rapport = {
        "lignes_lues": n_lues,
        "lignes_rejetees": avant - apres_filtre,
        "doublons_supprimes": apres_filtre - len(out),
        "lignes_valides": len(out),
        "date_min": out["date"].min() if len(out) else None,
        "date_max": out["date"].max() if len(out) else None,
        "ca_total": float(out["montant"].sum()) if len(out) else 0.0,
    }
    return out, rapport


def deviner_mapping(colonnes) -> dict:
    """Propose automatiquement une association colonnes source -> colonnes cible.
    Priorité : nom identique, puis commence par, puis contient. Une colonne n'est utilisée qu'une fois."""
    indices = {
        "date": ["date", "date_vente", "jour"],
        "produit": ["produit", "article", "designation", "désignation"],
        "categorie": ["categorie", "catégorie", "famille"],
        "quantite": ["quantite", "quantité", "qte", "qté"],
        "prix_unitaire": ["prix_unitaire", "pu", "prix"],
        "montant": ["montant", "total_ligne", "total", "ca"],
        "client": ["client", "nom_client", "acheteur"],
        "commercial": ["commercial", "vendeur", "agent", "representant", "représentant"],
    }
    norm = {col: str(col).lower().strip().replace(" ", "_").replace("-", "_") for col in colonnes}
    utilisees, res = set(), {}
    for cible, mots in indices.items():
        res[cible] = None
        for test in (lambda c, m: c == m, lambda c, m: c.startswith(m),
                     lambda c, m: len(m) > 3 and m in c):
            trouve = next((col for col, c in norm.items()
                           if col not in utilisees and any(test(c, m) for m in mots)), None)
            if trouve is not None:
                res[cible] = trouve
                utilisees.add(trouve)
                break
    return res
