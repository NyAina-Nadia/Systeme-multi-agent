"""
ETL piloté par le registre etl/agences_registre.json.
Ajouter une agence = ajouter un bloc dans le JSON (ou utiliser l'écran « Import de données »).
Usage :  python -m etl.etl_pipeline
"""
import json
from pathlib import Path
from etl.normalisation import lire_fichier, normaliser
from etl.loader import charger_agence

BASE_DIR = Path(__file__).resolve().parent.parent
DATA = BASE_DIR / "data"
REGISTRE = Path(__file__).resolve().parent / "agences_registre.json"


def charger_toutes_les_agences():
    config = json.loads(REGISTRE.read_text(encoding="utf-8"))["agences"]
    for a in config:
        df = lire_fichier(DATA / a["fichier"], sep=a.get("sep"), feuille=a.get("feuille"))
        ventes, rapport = normaliser(df, a["mapping"], a["agence"],
                                     a.get("format_date"), a.get("multiplicateur", 1))
        res = charger_agence(ventes, a.get("ville", ""), a.get("responsable", ""),
                             a.get("objectif", 0))
        print(f"{a['agence']:<14} {res['lignes_chargees']:>5} lignes "
              f"(rejetées : {rapport['lignes_rejetees']}, doublons : {rapport['doublons_supprimes']})")


if __name__ == "__main__":
    charger_toutes_les_agences()
