import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from app.auth import creer_utilisateur


if __name__ == "__main__":
    creer_utilisateur(
        nom="Administrateur",
        login="admin",
        mot_de_passe="ChangezMoi123",
        role="administrateur",
        id_agence=None,
    )
    print("Compte administrateur créé : login=admin / mot de passe=ChangezMoi123")
    print("Changez ce mot de passe dès votre première connexion.")