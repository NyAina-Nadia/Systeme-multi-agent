import sys
from PySide6.QtWidgets import QApplication, QMessageBox
from app.db import test_connexion
from app.theme import appliquer_theme
from app.audit import journaliser
from app.ui.login import LoginWindow
from app.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    appliquer_theme(app)                      # mode clair ou sombre mémorisé
    if not test_connexion():
        QMessageBox.critical(None, "Erreur", "Impossible de se connecter à la base "
                             "PostgreSQL. Vérifiez que le service est démarré et que "
                             "les identifiants du fichier .env sont corrects.")
        sys.exit(1)

    utilisateur = None
    while True:   # déconnexion et changement de thème sans quitter l'application
        if utilisateur is None:
            login = LoginWindow()
            if not login.exec():
                sys.exit(0)
            utilisateur = login.utilisateur_connecte
            journaliser(utilisateur["id"], "connexion", utilisateur["nom"])

        fenetre = MainWindow(utilisateur=utilisateur)
        fenetre.show()
        app.exec()

        if fenetre.action_fin == "theme":
            appliquer_theme(app)              # relit le mode mémorisé, garde la session
        elif fenetre.action_fin == "deconnexion":
            journaliser(utilisateur["id"], "deconnexion", utilisateur["nom"])
            utilisateur = None
        else:
            break


if __name__ == "__main__":
    main()
