from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QListWidget, QListWidgetItem,
                               QStackedWidget, QLabel, QFrame, QPushButton, QApplication, QSizePolicy)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon, QPixmap, QColor, QPainter, QBrush
from app.theme import P, sauver_mode
from app.ui.dashboard import DashboardScreen
from app.ui.multi_agences import MultiAgencesScreen
from app.ui.agents import AgentsScreen
from app.ui.produits_clients import ProduitsClientsScreen
from app.ui.prevision import PrevisionScreen
from app.ui.scenarios import ScenariosScreen
from app.ui.simulations import SimulationsScreen
from app.ui.evaluation_modeles import EvaluationModelesScreen
from app.ui.anomalies import AnomaliesScreen
from app.ui.segmentation import SegmentationScreen
from app.ui.recommandations import RecommandationsScreen
from app.ui.assistant_ia import AssistantIAScreen
from app.ui.rapports import RapportsScreen
from app.ui.agences import AgencesScreen
from app.ui.import_donnees import ImportDonneesScreen
from app.ui.utilisateurs import UtilisateursScreen
from app.ui.journal import JournalScreen

ADMIN   = {"administrateur"}
GESTION = {"administrateur", "responsable"}
TOUS    = {"administrateur", "responsable", "agent"}

# None = séparateur de section ; sinon (libellé, classe, rôles)
MENU = [
    None,
    ("📊  Tableau de bord",     DashboardScreen,       TOUS),
    ("🏢  Multi-agences",       MultiAgencesScreen,    GESTION),
    ("👤  Agents & objectifs",  AgentsScreen,          GESTION),
    ("📦  Produits & clients",  ProduitsClientsScreen, GESTION),
    None,
    ("📈  Prévision",           PrevisionScreen,       GESTION),
    ("🔮  Scénarios",           ScenariosScreen,       GESTION),
    ("🧪  Simulations",         SimulationsScreen,     GESTION),
    ("📉  Suivi des prévisions",EvaluationModelesScreen,GESTION),
    ("⚠️  Anomalies",           AnomaliesScreen,       GESTION),
    ("👥  Segmentation agents", SegmentationScreen,    GESTION),
    ("💡  Recommandations",     RecommandationsScreen, GESTION),
    ("🤖  Assistant IA",        AssistantIAScreen,     TOUS),
    None,
    ("📄  Rapports",            RapportsScreen,        GESTION),
    ("🏬  Agences",             AgencesScreen,         GESTION),
    ("📥  Import de données",   ImportDonneesScreen,   ADMIN),
    ("🔐  Utilisateurs",        UtilisateursScreen,    ADMIN),
    ("🧾  Journal d'audit",     JournalScreen,         ADMIN),
]

SECTIONS = ["ANALYSE", "INTELLIGENCE", "ADMINISTRATION"]


def _sep_widget(parent):
    """Petite ligne de séparation dans la sidebar."""
    f = QFrame(parent)
    f.setObjectName("sepSection")
    f.setFixedHeight(1)
    f.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    return f


class MainWindow(QMainWindow):
    def __init__(self, utilisateur):
        super().__init__()
        self.utilisateur = utilisateur
        self.action_fin  = "quitter"
        self.setWindowTitle("Suivi Performance Commerciale")
        self.resize(1380, 840)
        self.setMinimumSize(900, 600)

        central = QWidget()
        racine  = QHBoxLayout(central)
        racine.setContentsMargins(0, 0, 0, 0); racine.setSpacing(0)

        # ── SIDEBAR ──────────────────────────────────────────────────────────
        side = QFrame(); side.setObjectName("sidebar"); side.setFixedWidth(256)
        side.setMinimumWidth(220)
        ls = QVBoxLayout(side); ls.setContentsMargins(0, 0, 0, 0); ls.setSpacing(0)

        # Logo
        logo_w = QWidget(); logo_w.setObjectName("logoZone")
        logo_l = QVBoxLayout(logo_w); logo_l.setContentsMargins(0, 0, 0, 0); logo_l.setSpacing(0)
        logo = QLabel("◆ PerfCommerciale"); logo.setObjectName("logo")
        sub  = QLabel("Système intelligent multi-agences"); sub.setObjectName("logoSub")
        logo_l.addWidget(logo); logo_l.addWidget(sub)
        ls.addWidget(logo_w)

        # Menu
        self.menu  = QListWidget(); self.menu.setObjectName("menu")
        self.pages = QStackedWidget()
        self.menu.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        sec_index = 0          # index dans SECTIONS
        premier   = None
        for entree in MENU:
            if entree is None:
                # Séparateur + libellé de section
                if sec_index < len(SECTIONS):
                    sep = QListWidgetItem()
                    sep.setFlags(Qt.NoItemFlags)
                    sep.setSizeHint(QSize(0, 10))
                    self.menu.addItem(sep)
                    titre = QListWidgetItem("  " + SECTIONS[sec_index])
                    titre.setFlags(Qt.NoItemFlags)
                    f = QFont(); f.setPointSize(7); f.setBold(True)
                    titre.setFont(f)
                    self.menu.addItem(titre)
                    sec_index += 1
                continue

            libelle, classe_ecran, roles = entree
            if utilisateur["role"] not in roles:
                continue

            it = QListWidgetItem(libelle)
            it.setData(Qt.UserRole, self.pages.count())
            self.menu.addItem(it)
            if premier is None:
                premier = self.menu.row(it)

            page = QWidget(); page.setObjectName("page")
            lay  = QVBoxLayout(page)
            lay.setContentsMargins(28, 22, 28, 20); lay.setSpacing(0)
            lay.addWidget(classe_ecran(utilisateur=self.utilisateur))
            self.pages.addWidget(page)

        ls.addWidget(self.menu, 1)

        # Pied de sidebar : nom, rôle, boutons
        pied = QFrame(); pied.setObjectName("sidePied")
        pl   = QVBoxLayout(pied); pl.setContentsMargins(0, 10, 0, 10); pl.setSpacing(0)
        nom  = QLabel(utilisateur["nom"]); nom.setObjectName("utilisateur")
        role = QLabel(utilisateur["role"].capitalize()); role.setObjectName("role")
        pl.addWidget(nom); pl.addWidget(role)

        sombre = P["mode"] == "sombre"
        self.btn_theme = QPushButton("☀️  Mode clair" if sombre else "🌙  Mode sombre")
        self.btn_theme.setObjectName("themeBtn")
        self.btn_theme.setCursor(Qt.PointingHandCursor)
        self.btn_theme.clicked.connect(self.changer_theme)

        btn = QPushButton("⏻  Se déconnecter")
        btn.setObjectName("deconnexion"); btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self.se_deconnecter)

        pl.addWidget(self.btn_theme); pl.addWidget(btn)
        ls.addWidget(pied)

        # ── ZONE PRINCIPALE ──────────────────────────────────────────────────
        self.menu.currentItemChanged.connect(self._page_choisie)
        self.menu.setCurrentRow(premier if premier is not None else 0)

        racine.addWidget(side)
        racine.addWidget(self.pages, 1)
        self.setCentralWidget(central)

    def _page_choisie(self, courant, _precedent):
        if courant is not None and courant.data(Qt.UserRole) is not None:
            self.pages.setCurrentIndex(courant.data(Qt.UserRole))

    def changer_theme(self):
        sauver_mode("clair" if P["mode"] == "sombre" else "sombre")
        self.action_fin = "theme"
        self.close()

    def se_deconnecter(self):
        self.action_fin = "deconnexion"
        self.close()
