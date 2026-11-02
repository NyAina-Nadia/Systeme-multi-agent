"""Écran d'import : ajouter une nouvelle agence et ses ventes depuis un fichier CSV / Excel."""
import pandas as pd
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QComboBox,
                               QPushButton, QFileDialog, QLabel, QTableWidget, QMessageBox,
                               QScrollArea, QFrame, QApplication, QCheckBox)
from PySide6.QtCore import Qt
from etl.normalisation import (lire_fichier, normaliser, deviner_mapping, LIBELLES)
from etl.loader import charger_agence
from app.audit import journaliser
from app.ui.widgets import (TitrePage, Carte, etiquette, preparer_table, item, bouton_secondaire, fmt_ar)

SEPARATEURS = [("Détection automatique", None), ("Virgule  ,", ","), ("Point-virgule  ;", ";"), ("Tabulation", "\t")]
FORMATS_DATE = [("Détection automatique (jour en premier)", None), ("jj/mm/aaaa", "%d/%m/%Y"),
                ("aaaa-mm-jj", "%Y-%m-%d"), ("jj-mm-aaaa", "%d-%m-%Y")]
UNITES = [("Ariary (×1)", 1.0), ("Milliers d'Ariary — kAr (×1000)", 1000.0), ("Millions d'Ariary (×1 000 000)", 1e6)]


class ImportDonneesScreen(QWidget):
    def __init__(self, utilisateur):
        super().__init__()
        self.utilisateur = utilisateur
        self.df_source = None
        self.ventes_pretes = None
        self.chemin = None

        defil = QScrollArea(); defil.setWidgetResizable(True); defil.setFrameShape(QFrame.NoFrame)
        contenu = QWidget(); contenu.setObjectName("page")
        layout = QVBoxLayout(contenu); layout.setSpacing(14); layout.setContentsMargins(0, 0, 8, 0)
        defil.setWidget(contenu)
        ext = QVBoxLayout(self); ext.setContentsMargins(0, 0, 0, 0); ext.addWidget(defil)

        layout.addWidget(TitrePage("Import de données",
                                   "Ajoutez une nouvelle agence et ses ventes depuis un fichier CSV ou Excel"))

        # ---------- Étape 1 : fichier ----------
        c1 = Carte(); l1 = QVBoxLayout(c1)
        l1.addWidget(etiquette("① Choisir le fichier de ventes"))
        f1 = QFormLayout()
        ligne = QHBoxLayout()
        self.lbl_fichier = QLabel("Aucun fichier sélectionné"); self.lbl_fichier.setObjectName("sousTitre")
        b_parcourir = QPushButton("Parcourir…"); b_parcourir.clicked.connect(self.choisir_fichier)
        ligne.addWidget(b_parcourir); ligne.addWidget(self.lbl_fichier, 1)
        l1.addLayout(ligne)
        self.combo_sep = QComboBox(); [self.combo_sep.addItem(t, v) for t, v in SEPARATEURS]
        self.combo_feuille = QComboBox(); self.combo_feuille.setEnabled(False)
        f1.addRow("Séparateur (CSV)", self.combo_sep); f1.addRow("Feuille (Excel)", self.combo_feuille)
        l1.addLayout(f1)
        b_lire = bouton_secondaire(QPushButton("Lire le fichier")); b_lire.clicked.connect(self.lire)
        l1.addWidget(b_lire)
        layout.addWidget(c1)

        # ---------- Étape 2 : agence ----------
        c2 = Carte(); l2 = QVBoxLayout(c2)
        l2.addWidget(etiquette("② Informations sur l'agence"))
        f2 = QFormLayout()
        self.nom = QLineEdit(); self.nom.setPlaceholderText("ex. Toliara")
        self.ville = QLineEdit(); self.responsable = QLineEdit()
        self.objectif = QLineEdit(); self.objectif.setPlaceholderText("Objectif annuel en Ar, ex. 500000000")
        self.combo_unite = QComboBox(); [self.combo_unite.addItem(t, v) for t, v in UNITES]
        self.combo_date = QComboBox(); [self.combo_date.addItem(t, v) for t, v in FORMATS_DATE]
        f2.addRow("Nom de l'agence *", self.nom); f2.addRow("Ville", self.ville)
        f2.addRow("Responsable", self.responsable); f2.addRow("Objectif (Ar)", self.objectif)
        f2.addRow("Unité des montants du fichier", self.combo_unite); f2.addRow("Format des dates", self.combo_date)
        l2.addLayout(f2)
        layout.addWidget(c2)

        # ---------- Étape 3 : correspondance des colonnes ----------
        c3 = Carte(); l3 = QVBoxLayout(c3)
        l3.addWidget(etiquette("③ Associer les colonnes du fichier au modèle"))
        self.form_map = QFormLayout()
        self.combos_map = {}
        for cible, libelle in LIBELLES.items():
            cb = QComboBox(); cb.addItem("— aucune —", None)
            self.combos_map[cible] = cb
            self.form_map.addRow(libelle, cb)
        l3.addLayout(self.form_map)
        layout.addWidget(c3)

        # ---------- Étape 4 : contrôle + import ----------
        c4 = Carte(); l4 = QVBoxLayout(c4)
        l4.addWidget(etiquette("④ Contrôle qualité puis import"))
        b_apercu = bouton_secondaire(QPushButton("Vérifier les données (aperçu)")); b_apercu.clicked.connect(self.apercu)
        l4.addWidget(b_apercu)
        self.lbl_rapport = QLabel(""); self.lbl_rapport.setWordWrap(True); self.lbl_rapport.setObjectName("alerteNeutre")
        self.lbl_rapport.hide(); l4.addWidget(self.lbl_rapport)
        self.table = QTableWidget(); preparer_table(self.table); self.table.setMinimumHeight(220)
        l4.addWidget(self.table)
        self.chk_remplacer = QCheckBox("Remplacer toutes les ventes existantes de cette agence "
                                       "(décocher pour AJOUTER une nouvelle période sans effacer l'historique)")
        self.chk_remplacer.setChecked(True)
        l4.addWidget(self.chk_remplacer)
        self.btn_import = QPushButton("Importer dans la base de données")
        self.btn_import.setEnabled(False); self.btn_import.clicked.connect(self.importer)
        l4.addWidget(self.btn_import)
        layout.addWidget(c4)
        layout.addStretch()

    # ---------------------------------------------------------------
    def choisir_fichier(self):
        chemin, _ = QFileDialog.getOpenFileName(self, "Fichier de ventes", "",
                                                "Données (*.csv *.xlsx *.xls);;Tous les fichiers (*)")
        if not chemin:
            return
        self.chemin = chemin
        self.lbl_fichier.setText(chemin)
        self.combo_feuille.clear()
        if chemin.lower().endswith((".xlsx", ".xls", ".xlsm")):
            self.combo_feuille.setEnabled(True)
            self.combo_feuille.addItems(pd.ExcelFile(chemin).sheet_names)
        else:
            self.combo_feuille.setEnabled(False)
        if not self.nom.text():   # propose un nom d'agence d'après le fichier
            base = chemin.replace("\\", "/").split("/")[-1].rsplit(".", 1)[0]
            self.nom.setText(base.replace("agence_", "").replace("_", " ").title())
        self.lire()

    def lire(self):
        if not self.chemin:
            QMessageBox.information(self, "Fichier", "Choisissez d'abord un fichier."); return
        try:
            feuille = self.combo_feuille.currentText() if self.combo_feuille.isEnabled() else None
            self.df_source = lire_fichier(self.chemin, self.combo_sep.currentData(), feuille)
        except Exception as e:
            QMessageBox.critical(self, "Lecture impossible", str(e)[:300]); return
        colonnes = [str(c) for c in self.df_source.columns]
        devine = deviner_mapping(colonnes)
        for cible, cb in self.combos_map.items():
            cb.clear(); cb.addItem("— aucune —", None)
            for c in colonnes:
                cb.addItem(c, c)
            if devine.get(cible):
                cb.setCurrentIndex(cb.findData(devine[cible]))
        self.btn_import.setEnabled(False)
        self.lbl_rapport.setText(f"✓ {len(self.df_source)} lignes et {len(colonnes)} colonnes lues. "
                                 "Vérifiez l'association des colonnes (étape ③).")
        self.lbl_rapport.show()

    def _normaliser(self):
        if self.df_source is None:
            raise ValueError("Lisez d'abord un fichier (étape ①).")
        nom = self.nom.text().strip()
        if not nom:
            raise ValueError("Le nom de l'agence est obligatoire.")
        mapping = {c: cb.currentData() for c, cb in self.combos_map.items()}
        return normaliser(self.df_source, mapping, nom, self.combo_date.currentData(),
                          self.combo_unite.currentData())

    def apercu(self):
        try:
            self.ventes_pretes, r = self._normaliser()
        except Exception as e:
            self.btn_import.setEnabled(False)
            QMessageBox.warning(self, "Vérification", str(e)); return
        d0 = r["date_min"].strftime("%d/%m/%Y") if r["date_min"] is not None else "—"
        d1 = r["date_max"].strftime("%d/%m/%Y") if r["date_max"] is not None else "—"
        self.lbl_rapport.setText(
            f"Lignes lues : {r['lignes_lues']}  |  valides : {r['lignes_valides']}  |  "
            f"rejetées : {r['lignes_rejetees']}  |  doublons supprimés : {r['doublons_supprimes']}\n"
            f"Période : {d0} → {d1}  |  CA total : {fmt_ar(r['ca_total'])}")
        self.lbl_rapport.show()
        cols = list(self.ventes_pretes.columns)
        self.table.setColumnCount(len(cols)); self.table.setHorizontalHeaderLabels(cols)
        extrait = self.ventes_pretes.head(10)
        self.table.setRowCount(len(extrait))
        for i, (_, row) in enumerate(extrait.iterrows()):
            for j, c in enumerate(cols):
                v = row[c]
                v = v.strftime("%d/%m/%Y") if c == "date" else (f"{v:,.0f}" if isinstance(v, float) else v)
                self.table.setItem(i, j, item(v))
        self.table.resizeColumnsToContents()
        self.btn_import.setEnabled(r["lignes_valides"] > 0)

    def importer(self):
        if self.ventes_pretes is None or self.ventes_pretes.empty:
            return
        nom = self.ventes_pretes["agence"].iloc[0]
        rep = QMessageBox.question(self, "Confirmer l'import",
            f"Importer {len(self.ventes_pretes)} ventes pour l'agence « {nom} » ?\n\n"
            + ("Les ventes actuelles de cette agence seront REMPLACÉES." if self.chk_remplacer.isChecked()
             else "Les ventes seront AJOUTÉES à l'historique existant (vérifiez que les périodes ne se chevauchent pas)."))
        if rep != QMessageBox.Yes:
            return
        try:
            objectif = float(self.objectif.text().replace(" ", "") or 0)
        except ValueError:
            QMessageBox.warning(self, "Objectif", "L'objectif doit être un nombre."); return
        try:
            QApplication.setOverrideCursor(Qt.WaitCursor)
            res = charger_agence(self.ventes_pretes, self.ville.text().strip(),
                                 self.responsable.text().strip(), objectif,
                                 remplacer=self.chk_remplacer.isChecked())
        except Exception as e:
            QMessageBox.critical(self, "Import impossible", str(e)[:400]); return
        finally:
            QApplication.restoreOverrideCursor()
        journaliser(self.utilisateur["id"], "import_agence",
                    f"{res['agence']} : {res['lignes_chargees']} ventes "
                    f"({'remplacement' if self.chk_remplacer.isChecked() else 'ajout'})")
        QMessageBox.information(self, "Import terminé",
            f"{'Nouvelle agence créée' if res['creee'] else 'Agence mise à jour'} : {res['agence']}\n"
            f"{res['lignes_chargees']} ventes chargées.\n\n"
            "Redémarrez l'application (ou changez d'écran puis reconnectez-vous) "
            "pour que les listes d'agences et les graphiques se mettent à jour.")
        self.btn_import.setEnabled(False)
