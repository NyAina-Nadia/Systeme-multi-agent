from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QPushButton, QLabel
from app.audit import lister_journal
from app.ui.widgets import TitrePage, Carte, preparer_table, item, badge

COULEUR = {"connexion": "vert", "deconnexion": "gris", "import_agence": "ambre", "suppression_utilisateur": "rouge",
           "creation_utilisateur": "ambre"}


class JournalScreen(QWidget):
    def __init__(self, utilisateur):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        entete = QHBoxLayout()
        entete.addWidget(TitrePage("Journal d'audit", "Les 200 dernières actions sensibles : connexions, imports, comptes, objectifs"), 1)
        b = QPushButton("Actualiser"); b.clicked.connect(self.rafraichir)
        entete.addWidget(b)
        layout.addLayout(entete)

        carte = Carte(); lc = QVBoxLayout(carte); lc.setContentsMargins(18, 14, 18, 14)
        self.msg = QLabel(""); self.msg.setObjectName("alerteNeutre"); self.msg.setWordWrap(True); self.msg.hide()
        lc.addWidget(self.msg)
        self.table = QTableWidget(); preparer_table(self.table)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Date", "Utilisateur", "Action", "Détail"])
        lc.addWidget(self.table)
        layout.addWidget(carte, 1)
        self.rafraichir()

    def rafraichir(self):
        try:
            df = lister_journal(200)
        except Exception:
            self.msg.setText("La table journal_audit est introuvable. Exécutez sql/migration_v3.sql dans PostgreSQL.")
            self.msg.show(); self.table.setRowCount(0); return
        self.msg.hide()
        self.table.setRowCount(len(df))
        for i, (_, r) in enumerate(df.iterrows()):
            self.table.setItem(i, 0, item(r["date_action"].strftime("%d/%m/%Y %H:%M:%S")))
            self.table.setItem(i, 1, item(r["utilisateur"]))
            self.table.setCellWidget(i, 2, badge(r["action"], COULEUR.get(r["action"], "gris")))
            self.table.setItem(i, 3, item(r["detail"]))
        self.table.resizeColumnsToContents()
        self.table.horizontalHeader().setStretchLastSection(True)
