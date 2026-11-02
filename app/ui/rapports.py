import pandas as pd
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QCheckBox, QComboBox,
                               QDateEdit, QLabel, QFileDialog, QMessageBox, QScrollArea, QFrame)
from PySide6.QtCore import QDate
from app.db import engine
from reports.generate_report import generer_rapport_pdf
from reports.generate_excel import generer_export_excel, generer_export_personnalise, SECTIONS
from app.audit import journaliser
from app.ui.widgets import TitrePage, Carte, etiquette, bouton_secondaire, afficher_toast


class RapportsScreen(QWidget):
    def __init__(self, utilisateur):
        super().__init__()
        self.utilisateur = utilisateur
        defil = QScrollArea(); defil.setWidgetResizable(True); defil.setFrameShape(QFrame.NoFrame)
        contenu = QWidget(); contenu.setObjectName("page")
        layout = QVBoxLayout(contenu); layout.setSpacing(16); layout.setContentsMargins(0, 0, 10, 0)
        defil.setWidget(contenu)
        ext = QVBoxLayout(self); ext.setContentsMargins(0, 0, 0, 0); ext.addWidget(defil)

        layout.addWidget(TitrePage("Rapports", "Exports rapides (PDF, Excel) ou export personnalisé : vous choisissez le contenu"))

        rapide = Carte(); lr = QVBoxLayout(rapide); lr.setContentsMargins(18, 14, 18, 14)
        lr.addWidget(etiquette("Exports rapides"))
        ligne = QHBoxLayout()
        b_pdf = QPushButton("Exporter en PDF"); b_pdf.clicked.connect(self.exporter_pdf)
        b_xl = bouton_secondaire(QPushButton("Exporter en Excel (complet)")); b_xl.clicked.connect(self.exporter_excel)
        ligne.addWidget(b_pdf); ligne.addWidget(b_xl); ligne.addStretch()
        lr.addLayout(ligne)
        layout.addWidget(rapide)

        perso = Carte(); lp = QVBoxLayout(perso); lp.setContentsMargins(18, 14, 18, 14); lp.setSpacing(10)
        lp.addWidget(etiquette("Export Excel personnalisé"))
        note = QLabel("Cochez les feuilles à inclure, puis limitez éventuellement à une agence et à une période. "
                      "Les feuilles Anomalies, Segmentation et Recommandations portent sur toute la période."); note.setObjectName("sousTitre"); note.setWordWrap(True)
        lp.addWidget(note)
        grille = QGridLayout()
        self.cases = {}
        for i, (cle, libelle) in enumerate(SECTIONS.items()):
            c = QCheckBox(libelle); c.setChecked(cle in ("kpi", "mensuel", "agents"))
            self.cases[cle] = c
            grille.addWidget(c, i // 2, i % 2)
        lp.addLayout(grille)

        filtres = QHBoxLayout(); filtres.setSpacing(10)
        self.combo_agence = QComboBox(); self.combo_agence.addItem("Toutes les agences", None)
        for _, r in pd.read_sql("SELECT id_agence, agence FROM dim_agence ORDER BY agence", engine).iterrows():
            self.combo_agence.addItem(r["agence"], int(r["id_agence"]))
        self.case_periode = QCheckBox("Limiter à une période")
        self.d1 = QDateEdit(QDate(QDate.currentDate().year(), 1, 1)); self.d2 = QDateEdit(QDate.currentDate())
        for d in (self.d1, self.d2):
            d.setCalendarPopup(True); d.setDisplayFormat("dd/MM/yyyy"); d.setEnabled(False)
        self.case_periode.toggled.connect(lambda on: [d.setEnabled(on) for d in (self.d1, self.d2)])
        for w in (QLabel("Agence"), self.combo_agence, self.case_periode, self.d1, QLabel("au"), self.d2):
            filtres.addWidget(w)
        filtres.addStretch()
        lp.addLayout(filtres)

        b = QPushButton("Exporter la sélection…"); b.clicked.connect(self.exporter_personnalise)
        lp.addWidget(b)
        layout.addWidget(perso)
        layout.addStretch()

    def exporter_pdf(self):
        chemin = generer_rapport_pdf()
        journaliser(self.utilisateur["id"], "export_pdf", str(chemin))
        afficher_toast(self, f"Rapport PDF généré : {chemin}", "succes", 5000)

    def exporter_excel(self):
        chemin = generer_export_excel()
        journaliser(self.utilisateur["id"], "export_excel", str(chemin))
        afficher_toast(self, f"Fichier Excel généré : {chemin}", "succes", 5000)

    def exporter_personnalise(self):
        sections = [c for c, case in self.cases.items() if case.isChecked()]
        if not sections:
            QMessageBox.information(self, "Sélection", "Cochez au moins une feuille à exporter."); return
        chemin, _ = QFileDialog.getSaveFileName(self, "Enregistrer l'export", "export_personnalise.xlsx", "Excel (*.xlsx)")
        if not chemin:
            return
        d1 = self.d1.date().toPython() if self.case_periode.isChecked() else None
        d2 = self.d2.date().toPython() if self.case_periode.isChecked() else None
        try:
            generer_export_personnalise(chemin, sections, self.combo_agence.currentData(), d1, d2)
        except Exception as e:
            QMessageBox.critical(self, "Export impossible", str(e)[:400]); return
        journaliser(self.utilisateur["id"], "export_personnalise", f"{', '.join(sections)} -> {chemin}")
        afficher_toast(self, f"Export généré : {chemin}", "succes", 5000)
