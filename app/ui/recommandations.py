from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
                               QScrollArea, QFrame, QMessageBox, QApplication)
from PySide6.QtCore import Qt
from app.audit import journaliser
from app.theme import P
from app.ui.widgets import TitrePage, Carte, badge, bouton_secondaire, afficher_toast
from ml.recommandations import charger_recommandations
from ml.notifier import envoyer_alertes, configuration_manquante

TYPE_BADGE = {"Haute": "rouge", "Moyenne": "ambre", "Info": "vert"}


class RecommandationsScreen(QWidget):
    def __init__(self, utilisateur):
        super().__init__()
        self.utilisateur = utilisateur
        self.reco = []

        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        entete = QHBoxLayout()
        entete.addWidget(TitrePage("Recommandations",
                                   "Constats et actions proposées, générés par des règles explicites sur vos indicateurs"), 1)
        self.filtre = QComboBox(); self.filtre.addItems(["Toutes les priorités", "Haute", "Moyenne", "Info"])
        b_mail = bouton_secondaire(QPushButton("✉  Envoyer par e-mail")); b_mail.clicked.connect(self.envoyer)
        b_maj = QPushButton("Actualiser"); b_maj.clicked.connect(self.charger)
        entete.addWidget(self.filtre); entete.addWidget(b_mail); entete.addWidget(b_maj)
        layout.addLayout(entete)

        self.resume = QHBoxLayout(); self.resume.setSpacing(8)
        layout.addLayout(self.resume)

        self.defil = QScrollArea(); self.defil.setWidgetResizable(True); self.defil.setFrameShape(QFrame.NoFrame)
        self.contenu = QWidget(); self.contenu.setObjectName("page")
        self.liste = QVBoxLayout(self.contenu); self.liste.setSpacing(12); self.liste.setContentsMargins(0, 0, 10, 0)
        self.defil.setWidget(self.contenu)
        layout.addWidget(self.defil, 1)

        self.filtre.currentIndexChanged.connect(self.afficher)
        self.charger()

    def _vider(self, layout):
        while layout.count():
            it = layout.takeAt(0)
            if it.widget() is not None:
                it.widget().setParent(None)
            elif it.layout() is not None:
                self._vider(it.layout())

    def charger(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.reco = charger_recommandations()
        finally:
            QApplication.restoreOverrideCursor()
        self.afficher()

    def afficher(self):
        self._vider(self.liste); self._vider(self.resume)
        for prio in ("Haute", "Moyenne", "Info"):
            n = sum(r["priorite"] == prio for r in self.reco)
            self.resume.addWidget(badge(f"{n} {prio.lower()}", TYPE_BADGE[prio]))
        self.resume.addStretch()

        choix = self.filtre.currentText()
        liste = [r for r in self.reco if choix.startswith("Toutes") or r["priorite"] == choix]
        if not liste:
            vide = QLabel("✓  Rien à signaler pour ce filtre."); vide.setObjectName("alerteNeutre")
            self.liste.addWidget(vide)
        for r in liste:
            carte = Carte(); lc = QVBoxLayout(carte); lc.setContentsMargins(18, 14, 18, 14); lc.setSpacing(6)
            haut = QHBoxLayout()
            haut.addWidget(badge(r["priorite"], TYPE_BADGE[r["priorite"]]))
            haut.addWidget(badge(r["theme"], "gris"))
            nom = QLabel(r["agence"]); nom.setObjectName("section"); haut.addWidget(nom); haut.addStretch()
            lc.addLayout(haut)
            constat = QLabel(r["constat"]); constat.setWordWrap(True); lc.addWidget(constat)
            action = QLabel("→  " + r["action"]); action.setWordWrap(True); action.setObjectName("sousTitre")
            lc.addWidget(action)
            self.liste.addWidget(carte)
        self.liste.addStretch()

    def envoyer(self):
        manquantes = configuration_manquante()
        if manquantes:
            QMessageBox.information(self, "Configuration e-mail",
                "Pour envoyer les alertes par e-mail, ajoutez dans le fichier .env :\n\n" + "\n".join(manquantes) +
                "\n(et SMTP_PORT si différent de 587).")
            return
        try:
            envoye = envoyer_alertes(self.reco)
        except Exception as e:
            afficher_toast(self, "Envoi impossible : " + str(e)[:120], "erreur", 5000); return
        if envoye:
            journaliser(self.utilisateur["id"], "alertes_email", f"{len(self.reco)} recommandations")
            afficher_toast(self, "Alertes envoyées par e-mail", "succes")
        else:
            afficher_toast(self, "Rien d'urgent à envoyer", "info")
