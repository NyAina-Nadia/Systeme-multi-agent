import pandas as pd
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QComboBox,
                               QPushButton, QTableWidget, QMessageBox, QInputDialog)
from app.db import engine
from app.auth import (creer_utilisateur, lister_utilisateurs, changer_mot_de_passe,
                      supprimer_utilisateur)
from app.audit import journaliser
from app.ui.widgets import afficher_toast, TitrePage, Carte, etiquette, preparer_table, item, bouton_secondaire, bouton_danger


class UtilisateursScreen(QWidget):
    def __init__(self, utilisateur):
        super().__init__()
        self.utilisateur = utilisateur
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(TitrePage("Utilisateurs", "Comptes d'accès et rôles (administrateur, responsable, agent)"))

        self.table = QTableWidget(); preparer_table(self.table)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Nom", "Identifiant", "Rôle", "Agence"])
        layout.addWidget(self.table, 1)

        ligne = QHBoxLayout()
        b_mdp = bouton_secondaire(QPushButton("Réinitialiser le mot de passe"))
        b_mdp.clicked.connect(self.reinitialiser_mdp)
        b_sup = bouton_danger(QPushButton("Supprimer"))
        b_sup.clicked.connect(self.supprimer)
        ligne.addWidget(b_mdp); ligne.addWidget(b_sup); ligne.addStretch()
        layout.addLayout(ligne)

        carte = Carte(); lc = QVBoxLayout(carte)
        lc.addWidget(etiquette("Créer un compte"))
        form = QFormLayout()
        self.nom = QLineEdit(); self.login = QLineEdit()
        self.mdp = QLineEdit(); self.mdp.setEchoMode(QLineEdit.Password)
        self.mdp.setPlaceholderText("8 caractères minimum")
        self.role = QComboBox(); self.role.addItems(["agent", "responsable", "administrateur"])
        self.agence = QComboBox()
        form.addRow("Nom complet", self.nom); form.addRow("Identifiant", self.login)
        form.addRow("Mot de passe", self.mdp); form.addRow("Rôle", self.role)
        form.addRow("Agence", self.agence)
        lc.addLayout(form)
        b_creer = QPushButton("Créer le compte"); b_creer.clicked.connect(self.creer)
        lc.addWidget(b_creer)
        layout.addWidget(carte)

        self.charger_agences()
        self.rafraichir()

    def charger_agences(self):
        self.agence.clear()
        self.agence.addItem("— aucune (accès global) —", None)
        df = pd.read_sql("SELECT id_agence, agence FROM dim_agence ORDER BY agence", engine)
        for _, r in df.iterrows():
            self.agence.addItem(r["agence"], int(r["id_agence"]))

    def rafraichir(self):
        df = lister_utilisateurs()
        self.table.setRowCount(len(df))
        for i, (_, r) in enumerate(df.iterrows()):
            for j, col in enumerate(["id_utilisateur", "nom", "login", "role", "agence"]):
                self.table.setItem(i, j, item(r[col]))
        self.table.resizeColumnsToContents()

    def _selection(self):
        ligne = self.table.currentRow()
        if ligne < 0:
            QMessageBox.information(self, "Sélection", "Sélectionnez d'abord un utilisateur dans le tableau.")
            return None
        return int(self.table.item(ligne, 0).text()), self.table.item(ligne, 2).text()

    def creer(self):
        nom, login, mdp = self.nom.text().strip(), self.login.text().strip(), self.mdp.text()
        role, id_agence = self.role.currentText(), self.agence.currentData()
        if not nom or not login:
            QMessageBox.warning(self, "Champs manquants", "Le nom et l'identifiant sont obligatoires."); return
        if len(mdp) < 8:
            QMessageBox.warning(self, "Mot de passe", "Le mot de passe doit contenir au moins 8 caractères."); return
        if role == "agent" and id_agence is None:
            QMessageBox.warning(self, "Agence", "Un agent doit être rattaché à une agence."); return
        try:
            creer_utilisateur(nom, login, mdp, role, id_agence)
        except Exception as e:
            QMessageBox.critical(self, "Création impossible",
                                 "Cet identifiant existe peut-être déjà.\n\n" + str(e)[:200]); return
        journaliser(self.utilisateur["id"], "creation_utilisateur", f"{login} ({role})")
        for c in (self.nom, self.login, self.mdp):
            c.clear()
        self.rafraichir(); afficher_toast(self, f"Compte « {login} » créé", "succes")

    def reinitialiser_mdp(self):
        sel = self._selection()
        if not sel: return
        nouveau, ok = QInputDialog.getText(self, "Nouveau mot de passe",
                                           f"Nouveau mot de passe pour « {sel[1]} » :", QLineEdit.Password)
        if ok and len(nouveau) >= 8:
            changer_mot_de_passe(sel[0], nouveau)
            journaliser(self.utilisateur["id"], "reinit_mot_de_passe", sel[1])
            afficher_toast(self, "Mot de passe modifié", "succes")
        elif ok:
            QMessageBox.warning(self, "Mot de passe", "8 caractères minimum.")

    def supprimer(self):
        sel = self._selection()
        if not sel: return
        if sel[0] == self.utilisateur["id"]:
            QMessageBox.warning(self, "Suppression", "Vous ne pouvez pas supprimer votre propre compte."); return
        if QMessageBox.question(self, "Confirmer", f"Supprimer le compte « {sel[1]} » ?") == QMessageBox.Yes:
            supprimer_utilisateur(sel[0])
            journaliser(self.utilisateur["id"], "suppression_utilisateur", sel[1])
            self.rafraichir(); afficher_toast(self, "Compte supprimé", "info")
