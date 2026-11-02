import pandas as pd
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
QTableWidgetItem, QLabel, QLineEdit, QPushButton,
QFormLayout, QMessageBox)
from app.db import engine
from app.ui.widgets import TitrePage, preparer_table, bouton_secondaire, Carte
class AgencesScreen(QWidget):
    def __init__(self, utilisateur):
        super().__init__()

        self.utilisateur = utilisateur
        self.id_en_edition = None
        layout = QVBoxLayout(self)

        layout.addWidget(TitrePage("Gestion des agences", "Créer ou modifier une agence, son responsable et son objectif"))
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Agence", "Ville", "Responsable", "Objectif (Ar)"])
        self.table.cellClicked.connect(self.selectionner_ligne)
        preparer_table(self.table)
        layout.addWidget(self.table)

# --- Formulaire d'ajout / modification ---

        formulaire = QFormLayout()
        self.champ_agence = QLineEdit()
        self.champ_ville = QLineEdit()
        self.champ_responsable = QLineEdit()
        self.champ_objectif = QLineEdit()
        formulaire.addRow("Agence", self.champ_agence)
        formulaire.addRow("Ville", self.champ_ville)
        formulaire.addRow("Responsable", self.champ_responsable)
        formulaire.addRow("Objectif (Ar)", self.champ_objectif)
        layout.addLayout(formulaire)
        boutons = QHBoxLayout()
        bouton_enregistrer = QPushButton("Enregistrer")
        bouton_enregistrer.clicked.connect(self.enregistrer)
        bouton_nouveau = bouton_secondaire(QPushButton("Nouvelle agence (vider le formulaire)"))
        bouton_nouveau.clicked.connect(self.vider_formulaire)
        boutons.addWidget(bouton_enregistrer)
        boutons.addWidget(bouton_nouveau)
        layout.addLayout(boutons)
        self.rafraichir()

    def rafraichir(self):
        df = pd.read_sql("SELECT id_agence, agence, ville, responsable, objectif "
            "FROM dim_agence ORDER BY agence", engine)
        self.table.setRowCount(len(df))
        for i, (_, row) in enumerate(df.iterrows()):
            self.table.setItem(i, 0, QTableWidgetItem(str(row["id_agence"])))
            self.table.setItem(i, 1, QTableWidgetItem(str(row["agence"])))
            self.table.setItem(i, 2, QTableWidgetItem(str(row["ville"] or "")))
            self.table.setItem(i, 3, QTableWidgetItem(str(row["responsable"] or "")))
            self.table.setItem(i, 4, QTableWidgetItem(f"{row['objectif'] or 0:,.0f}"))

    def selectionner_ligne(self, ligne, colonne):
        self.id_en_edition = int(self.table.item(ligne, 0).text())
        self.champ_agence.setText(self.table.item(ligne, 1).text())
        self.champ_ville.setText(self.table.item(ligne, 2).text())
        self.champ_responsable.setText(self.table.item(ligne, 3).text())
        self.champ_objectif.setText(self.table.item(ligne, 4).text().replace(" ", ""))

    def vider_formulaire(self):
        self.id_en_edition = None
        for champ in (self.champ_agence, self.champ_ville, self.champ_responsable, self.champ_objectif):
            champ.clear()

    def enregistrer(self):
        nom = self.champ_agence.text().strip()
        if not nom:
            QMessageBox.warning(self, "Champ manquant", "Le nom de l'agence est obligatoire.")
            return
        try:
            objectif = float(self.champ_objectif.text().replace(" ", "") or 0)
        except ValueError:
            QMessageBox.warning(self, "Valeur invalide", "L'objectif doit être un nombre.")
            return
        with engine.begin() as conn:
            if self.id_en_edition is None:
                conn.exec_driver_sql(
                    "INSERT INTO dim_agence (agence, ville, responsable, objectif) "
                    "VALUES (%s, %s, %s, %s)",
                    (nom, self.champ_ville.text(), self.champ_responsable.text(), objectif),
                )
            else:
                conn.exec_driver_sql(
                    "UPDATE dim_agence SET agence=%s, ville=%s, responsable=%s, objectif=%s "
                    "WHERE id_agence=%s",
                    (nom, self.champ_ville.text(), self.champ_responsable.text(),
                     objectif, self.id_en_edition),
                )
        self.vider_formulaire()
        self.rafraichir()


