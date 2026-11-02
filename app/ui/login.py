from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLineEdit, QPushButton, QLabel,
                               QMessageBox, QHBoxLayout, QFrame)
from PySide6.QtCore import Qt
from app.auth import authentifier
from app.theme import P
from app.ui.widgets import ombre


class LoginWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Connexion — Suivi Performance Commerciale")
        self.setFixedSize(820, 480)
        self.utilisateur_connecte = None

        racine = QHBoxLayout(self)
        racine.setContentsMargins(0, 0, 0, 0)
        racine.setSpacing(0)

        # --- Panneau gauche (identité) ---
        gauche = QFrame()
        gauche.setStyleSheet("QFrame { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,"
                             "stop:0 #0E4749, stop:1 #197A7D); }")
        lg = QVBoxLayout(gauche)
        lg.setContentsMargins(40, 40, 40, 40)
        lg.addStretch()
        titre = QLabel("Suivi de la performance\ncommerciale multi-agences")
        titre.setStyleSheet("color:white; font-size:26px; font-weight:700; background:transparent;")
        sous = QLabel("Tableaux de bord · Prévisions · Détection d'anomalies · Assistant IA")
        sous.setWordWrap(True)
        sous.setStyleSheet("color:#BFE0DE; font-size:13px; background:transparent;")
        lg.addWidget(titre); lg.addSpacing(10); lg.addWidget(sous); lg.addStretch()
        racine.addWidget(gauche, 5)

        # --- Panneau droit (formulaire) ---
        droite = QFrame()
        droite.setObjectName("loginDroite")
        droite.setStyleSheet(f"QFrame#loginDroite {{ background: {P['fond']}; }}")
        ld = QVBoxLayout(droite)
        ld.setContentsMargins(44, 40, 44, 40)
        ld.addStretch()
        bienvenue = QLabel("Bienvenue 👋")
        bienvenue.setObjectName("titrePage")
        info = QLabel("Connectez-vous pour accéder à vos indicateurs.")
        info.setObjectName("sousTitre")
        ld.addWidget(bienvenue); ld.addWidget(info); ld.addSpacing(18)

        ld.addWidget(QLabel("Identifiant"))
        self.champ_login = QLineEdit(); self.champ_login.setPlaceholderText("ex. admin")
        ld.addWidget(self.champ_login)
        ld.addSpacing(6)
        ld.addWidget(QLabel("Mot de passe"))
        self.champ_mdp = QLineEdit(); self.champ_mdp.setEchoMode(QLineEdit.Password)
        self.champ_mdp.setPlaceholderText("••••••••")
        ld.addWidget(self.champ_mdp)
        ld.addSpacing(14)

        bouton = QPushButton("Se connecter")
        bouton.setCursor(Qt.PointingHandCursor)
        bouton.setMinimumHeight(40)
        bouton.clicked.connect(self.tenter_connexion)
        ld.addWidget(bouton)
        ld.addStretch()
        racine.addWidget(droite, 4)

        self.champ_login.returnPressed.connect(self.champ_mdp.setFocus)
        self.champ_mdp.returnPressed.connect(self.tenter_connexion)

    def tenter_connexion(self):
        utilisateur = authentifier(self.champ_login.text().strip(), self.champ_mdp.text())
        if utilisateur is None:
            QMessageBox.warning(self, "Erreur", "Identifiant ou mot de passe invalide.")
            self.champ_mdp.clear(); self.champ_mdp.setFocus()
            return
        self.utilisateur_connecte = utilisateur
        self.accept()
