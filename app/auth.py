import bcrypt
import pandas as pd
from app.db import engine

def creer_utilisateur(nom, login, mot_de_passe, role, id_agence=None):
    hash_mdp = bcrypt.hashpw(mot_de_passe.encode(), bcrypt.gensalt()).decode()
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "INSERT INTO utilisateur (nom, login, mot_de_passe_hash, role, id_agence) VALUES (%s, %s, %s, %s, %s)",
            (nom, login, hash_mdp, role, id_agence),
        )
def authentifier(login, mot_de_passe):
    df = pd.read_sql(
        "SELECT id_utilisateur, nom, login, mot_de_passe_hash, role, id_agence "
        "FROM utilisateur WHERE login = %(login)s",
        engine,
        params={"login": login},
    )

    if df.empty:
        return None

    ligne = df.iloc[0]

    if bcrypt.checkpw(mot_de_passe.encode(), ligne["mot_de_passe_hash"].encode()):
        return {
            "id": int(ligne["id_utilisateur"]),
            "nom": ligne["nom"],
            "role": ligne["role"],
            "id_agence": None if pd.isna(ligne["id_agence"]) else int(ligne["id_agence"]),
        }

    return None

def lister_utilisateurs():
    return pd.read_sql(
        "SELECT u.id_utilisateur, u.nom, u.login, u.role, COALESCE(a.agence, '—') AS agence "
        "FROM utilisateur u LEFT JOIN dim_agence a ON a.id_agence = u.id_agence "
        "ORDER BY u.nom", engine)


def changer_mot_de_passe(id_utilisateur, nouveau_mot_de_passe):
    hash_mdp = bcrypt.hashpw(nouveau_mot_de_passe.encode(), bcrypt.gensalt()).decode()
    with engine.begin() as conn:
        conn.exec_driver_sql(
            "UPDATE utilisateur SET mot_de_passe_hash = %s WHERE id_utilisateur = %s",
            (hash_mdp, id_utilisateur))


def supprimer_utilisateur(id_utilisateur):
    with engine.begin() as conn:
        conn.exec_driver_sql("DELETE FROM utilisateur WHERE id_utilisateur = %s", (id_utilisateur,))
