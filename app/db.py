import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

# Charger les variables du fichier .env
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Configuration de PostgreSQL
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "3010")
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "performance_commerciale")

# Vérifier la présence du mot de passe
if not DB_PASSWORD:
    raise ValueError(
        "Le mot de passe PostgreSQL est absent. "
        "Vérifiez la variable DB_PASSWORD dans le fichier .env."
    )

# URL de connexion
DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# Création du moteur SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)


def test_connexion() -> bool:
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")

        print("Connexion à PostgreSQL réussie.")
        return True

    except Exception as e:
        print("Erreur de connexion à PostgreSQL :", e)
        return False
