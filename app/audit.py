"""Journal d'audit : trace qui a fait quoi. Ne doit jamais faire planter l'application."""
import pandas as pd
from app.db import engine


def journaliser(id_utilisateur, action: str, detail: str = ""):
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql(
                "INSERT INTO journal_audit (id_utilisateur, action, detail) VALUES (%s, %s, %s)",
                (id_utilisateur, action, detail[:500]))
    except Exception as e:   # table absente, base indisponible...
        print("Audit non enregistré :", e)


def lister_journal(limite: int = 200) -> pd.DataFrame:
    return pd.read_sql(
        "SELECT j.date_action, COALESCE(u.nom, '—') AS utilisateur, j.action, COALESCE(j.detail, '') AS detail "
        "FROM journal_audit j LEFT JOIN utilisateur u ON u.id_utilisateur = j.id_utilisateur "
        "ORDER BY j.date_action DESC LIMIT %(n)s", engine, params={"n": int(limite)})
