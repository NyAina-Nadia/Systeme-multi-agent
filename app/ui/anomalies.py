from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QPushButton, QComboBox)
from ml.anomalies import detecter_anomalies
from app.ui.widgets import TitrePage, Carte, preparer_table, item, fmt_ar, badge

BADGE = {"Élevé": "rouge", "Moyen": "ambre", "Faible": "vert"}


class AnomaliesScreen(QWidget):
    def __init__(self, utilisateur):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        entete = QHBoxLayout()
        entete.addWidget(TitrePage("Anomalies", "Isolation Forest + règles de contrôle métier : chaque alerte est expliquée"), 1)
        self.filtre = QComboBox(); self.filtre.addItems(["Tous les niveaux", "Élevé", "Moyen", "Faible"])
        bouton = QPushButton("Relancer la détection"); bouton.clicked.connect(self.rafraichir)
        entete.addWidget(self.filtre); entete.addWidget(bouton)
        layout.addLayout(entete)

        self.resume = QHBoxLayout(); self.resume.setSpacing(8)
        layout.addLayout(self.resume)

        info = QLabel("Élevé : atypique ET confirmée par une règle (prix, quantité, montant incohérent…). "
                      "Moyen : une règle seule, ou atypique sans explication. "
                      "Faible : atypique mais justifiée par le catalogue (grosse vente non suspecte).")
        info.setObjectName("sousTitre"); info.setWordWrap(True)
        layout.addWidget(info)

        carte = Carte(); lc = QVBoxLayout(carte); lc.setContentsMargins(18, 14, 18, 14)
        self.table = QTableWidget(); preparer_table(self.table)
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(["Agence", "Produit", "Quantité", "Montant", "Niveau", "Score", "Explication"])
        self.table.setMinimumHeight(380)
        lc.addWidget(self.table)
        layout.addWidget(carte, 1)

        self.df = None
        self.filtre.currentIndexChanged.connect(self.afficher)
        self.rafraichir()

    def rafraichir(self, *_):
        self.df = detecter_anomalies(top_n=200)
        self.afficher()

    def afficher(self, *_):
        while self.resume.count():
            it = self.resume.takeAt(0)
            if it.widget() is not None:
                it.widget().hide(); it.widget().deleteLater()
        df = self.df
        if df is None:
            return
        for n in ("Élevé", "Moyen", "Faible"):
            self.resume.addWidget(badge(f"{int((df['niveau'] == n).sum())} {n.lower()}", BADGE[n]))
        self.resume.addStretch()
        choix = self.filtre.currentText()
        if choix in BADGE:
            df = df[df["niveau"] == choix]
        self.table.setRowCount(len(df))
        for i, (_, r) in enumerate(df.iterrows()):
            self.table.setItem(i, 0, item(r["agence"]))
            self.table.setItem(i, 1, item(r["produit"]))
            self.table.setItem(i, 2, item(int(r["quantite"]), True))
            self.table.setItem(i, 3, item(fmt_ar(float(r["montant"]), False), True))
            self.table.setCellWidget(i, 4, badge(r["niveau"], BADGE[r["niveau"]]))
            self.table.setItem(i, 5, item(f"{float(r['score']):.3f}", True))
            self.table.setItem(i, 6, item(r["motifs"]))
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)
