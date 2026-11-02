
import json
import os

import pyqtgraph as pg

from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import QApplication


# ============================================================
# 1. COULEURS PRINCIPALES
# ============================================================

PRIMAIRE = "#0E4749"
ACCENT = "#E0703F"
OR = "#D9A02B"
SUCCES = "#2E9E6B"
DANGER = "#D6453D"


# ============================================================
# 2. THÈME CLAIR
# ============================================================

LIGHT = {
    "nom": "clair",
    "mode": "clair",

    "fond": "#F3F6F7",
    "carte": "#FFFFFF",
    "bordure": "#E1E8E8",

    "texte": "#26383B",
    "doux": "#718387",
    "titre": "#123C3E",

    "bouton": PRIMAIRE,
    "bouton_hover": "#155B5D",
    "bouton_txt": "#FFFFFF",

    "sec_bg": "#EAF1F1",
    "sec_hover": "#DCE8E8",
    "sec_txt": PRIMAIRE,

    "sidebar": "#0B3436",
    "sidebar_hover": "#16494B",
    "sidebar_actif": "#1A5A5B",
    "sidebar_txt": "#E9F3F3",
    "sidebar_doux": "#A8C0C1",

    "ligne_alt": "#F5F8F8",
    "entete_bg": "#EAF0F0",
    "entete_txt": "#244749",
    "selection": "#D7EAEA",

    "input_bg": "#FFFFFF",
    "input_bordure": "#D4DFDF",
    "input_focus": PRIMAIRE,

    "ombre": "#000000",
    "sep_side": "#275052",

    "risque_bg": "#FCEDEC",
    "risque_bordure": "#F3C6C2",
    "risque_txt": "#A9322C",

    "positif_bg": "#E9F7EF",
    "positif_bordure": "#BFE6CD",
    "positif_txt": "#217447",

    "neutre_bg": "#EAF3F5",
    "neutre_bordure": "#C9E0E5",
    "neutre_txt": "#285D68",

    "ambre_bg": "#FFF5DF",
    "ambre_bordure": "#F0D99C",
    "ambre_txt": "#8A6415",

    "serie1": "#0E7C7B",
    "serie2": ACCENT,
    "serie3": OR,
    "grille": "#E1E8E8",

    "succes": SUCCES,
    "danger": DANGER,
    "accent": ACCENT,
    "or": OR,
    "primaire": PRIMAIRE,
}


# ============================================================
# 3. THÈME SOMBRE
# ============================================================

DARK = {
    "nom": "sombre",
    "mode": "sombre",

    "fond": "#101C1F",
    "carte": "#17272B",
    "bordure": "#294044",

    "texte": "#E4EEEE",
    "doux": "#A0B5B8",
    "titre": "#F0F8F8",

    "bouton": "#287779",
    "bouton_hover": "#328D8F",
    "bouton_txt": "#FFFFFF",

    "sec_bg": "#233B40",
    "sec_hover": "#304D52",
    "sec_txt": "#D9EEEE",

    "sidebar": "#0A171A",
    "sidebar_hover": "#173237",
    "sidebar_actif": "#1E484D",
    "sidebar_txt": "#E2EEEE",
    "sidebar_doux": "#9BB6B9",

    "ligne_alt": "#1B3034",
    "entete_bg": "#20373B",
    "entete_txt": "#DDEBEC",
    "selection": "#285356",

    "input_bg": "#132327",
    "input_bordure": "#355055",
    "input_focus": "#3CC6C0",

    "ombre": "#000000",
    "sep_side": "#29484C",

    "risque_bg": "#3A2426",
    "risque_bordure": "#704044",
    "risque_txt": "#FFAAA5",

    "positif_bg": "#1C352A",
    "positif_bordure": "#315B43",
    "positif_txt": "#91E0AE",

    "neutre_bg": "#1C333A",
    "neutre_bordure": "#31545D",
    "neutre_txt": "#A8DCE7",

    "ambre_bg": "#3A3020",
    "ambre_bordure": "#6B5730",
    "ambre_txt": "#F1D18A",

    "serie1": "#3CC6C0",
    "serie2": "#F28B5C",
    "serie3": "#EDB947",
    "grille": "#294044",

    "succes": "#53C98A",
    "danger": "#FF7770",
    "accent": "#F28B5C",
    "or": "#EDB947",
    "primaire": "#3CC6C0",
}


# ============================================================
# 4. PALETTE ACTIVE
# ============================================================

P = LIGHT.copy()


def definir_mode(mode="clair"):
    """Change la palette active de l'application."""
    global P

    mode = str(mode).strip().lower()
    sombre = mode in ("sombre", "dark")

    P.clear()
    P.update(DARK if sombre else LIGHT)

    # Compatibilité avec MainWindow
    P["mode"] = "sombre" if sombre else "clair"
    P["nom"] = P["mode"]

    return P


# ============================================================
# 5. FICHIER DE CONFIGURATION
# ============================================================

def _chemin_configuration():
    """Chemin du fichier de sauvegarde du thème."""
    chemin_personnalise = os.environ.get("THEME_CONFIG_PATH")

    if chemin_personnalise:
        return chemin_personnalise

    dossier = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(dossier, "theme_config.json")


def charger_mode():
    """Charge le thème enregistré ou utilise le thème clair."""
    chemin = _chemin_configuration()

    try:
        if os.path.exists(chemin):
            with open(chemin, "r", encoding="utf-8") as fichier:
                configuration = json.load(fichier)

            mode = str(
                configuration.get("mode", "clair")
            ).strip().lower()

            if mode in ("clair", "sombre", "light", "dark"):
                return mode

    except (OSError, ValueError, TypeError) as erreur:
        print(f"Lecture du thème impossible : {erreur}")

    return "clair"


def enregistrer_mode(mode):
    """Enregistre le thème sélectionné."""
    mode = str(mode).strip().lower()

    if mode in ("sombre", "dark"):
        mode = "sombre"
    else:
        mode = "clair"

    chemin = _chemin_configuration()

    try:
        dossier = os.path.dirname(chemin)

        if dossier:
            os.makedirs(dossier, exist_ok=True)

        with open(chemin, "w", encoding="utf-8") as fichier:
            json.dump(
                {"mode": mode},
                fichier,
                ensure_ascii=False,
                indent=4,
            )

        return True

    except OSError as erreur:
        print(f"Enregistrement du thème impossible : {erreur}")
        return False


def sauver_mode(mode):
    """
    Alias compatible avec les modules qui utilisent
    encore sauver_mode().
    """
    return enregistrer_mode(mode)


# ============================================================
# 6. FEUILLE DE STYLE GLOBALE
# ============================================================

def construire_qss():
    """Construit la feuille de style Qt selon la palette active."""

    return f"""
    /* FONDS GÉNÉRAUX */

    QWidget {{
        color: {P["texte"]};
        font-family: "Segoe UI";
        font-size: 12px;
    }}

    QWidget#page {{
        background-color: {P["fond"]};
    }}

    QMainWindow,
    QDialog {{
        background-color: {P["fond"]};
    }}

    QLabel {{
        background-color: transparent;
        color: {P["texte"]};
    }}

    QLabel#titrePage {{
        color: {P["titre"]};
        font-size: 24px;
        font-weight: 800;
    }}

    QLabel#sousTitre {{
        color: {P["doux"]};
        font-size: 11px;
    }}

    /* CARTES */

    QFrame#carte {{
        background-color: {P["carte"]};
        border: 1px solid {P["bordure"]};
        border-radius: 14px;
    }}

    /* KPI */

    QLabel#kpiLibelle {{
        color: {P["doux"]};
        font-size: 10px;
        font-weight: 700;
    }}

    QLabel#kpiValeur {{
        color: {P["titre"]};
        font-size: 23px;
        font-weight: 800;
    }}

    QLabel#kpiSous {{
        color: {P["doux"]};
        font-size: 10px;
    }}

    QLabel#kpiIcone {{
        color: {P["serie1"]};
        font-size: 20px;
        font-weight: 700;
    }}

    /* BOUTONS */

    QPushButton {{
        background-color: {P["bouton"]};
        color: {P["bouton_txt"]};
        border: 1px solid {P["bouton"]};
        border-radius: 8px;
        padding: 9px 15px;
        font-weight: 600;
    }}

    QPushButton:hover {{
        background-color: {P["bouton_hover"]};
        border-color: {P["bouton_hover"]};
    }}

    QPushButton:pressed {{
        background-color: {P["primaire"]};
    }}

    QPushButton:disabled {{
        background-color: {P["sec_bg"]};
        color: {P["doux"]};
        border-color: {P["bordure"]};
    }}

    QPushButton#boutonSecondaire {{
        background-color: {P["sec_bg"]};
        color: {P["sec_txt"]};
        border: 1px solid {P["bordure"]};
    }}

    QPushButton#boutonSecondaire:hover {{
        background-color: {P["sec_hover"]};
    }}

    QPushButton#themeBtn {{
        background-color: {P["sidebar_hover"]};
        color: {P["sidebar_txt"]};
        border: 1px solid {P["sep_side"]};
        border-radius: 7px;
        padding: 9px 10px;
        text-align: left;
    }}

    QPushButton#themeBtn:hover {{
        background-color: {P["sidebar_actif"]};
    }}

    QPushButton#deconnexion {{
        background-color: transparent;
        color: {P["sidebar_txt"]};
        border: 1px solid {P["sep_side"]};
        border-radius: 7px;
        padding: 9px 10px;
        text-align: left;
    }}

    QPushButton#deconnexion:hover {{
        background-color: {P["risque_bg"]};
        color: {P["risque_txt"]};
    }}

    /* CHAMPS DE SAISIE */

    QLineEdit,
    QTextEdit,
    QPlainTextEdit,
    QSpinBox,
    QDoubleSpinBox,
    QDateEdit,
    QDateTimeEdit,
    QTimeEdit {{
        background-color: {P["input_bg"]};
        color: {P["texte"]};
        border: 1px solid {P["input_bordure"]};
        border-radius: 8px;
        padding: 8px 10px;
        selection-background-color: {P["selection"]};
        selection-color: {P["texte"]};
    }}

    QLineEdit:focus,
    QTextEdit:focus,
    QPlainTextEdit:focus,
    QSpinBox:focus,
    QDoubleSpinBox:focus,
    QDateEdit:focus,
    QDateTimeEdit:focus,
    QTimeEdit:focus {{
        border: 1px solid {P["input_focus"]};
    }}

    /* LISTES DÉROULANTES */

    QComboBox {{
        background-color: {P["input_bg"]};
        color: {P["texte"]};
        border: 1px solid {P["input_bordure"]};
        border-radius: 8px;
        padding: 7px 10px;
        min-height: 20px;
    }}

    QComboBox:hover,
    QComboBox:focus {{
        border: 1px solid {P["input_focus"]};
    }}

    QComboBox::drop-down {{
        border: none;
        width: 28px;
    }}

    QComboBox QAbstractItemView {{
        background-color: {P["carte"]};
        color: {P["texte"]};
        border: 1px solid {P["bordure"]};
        selection-background-color: {P["selection"]};
        selection-color: {P["texte"]};
        outline: none;
        padding: 4px;
    }}

    /* TABLEAUX */

    QTableWidget,
    QTableView {{
        background-color: {P["carte"]};
        alternate-background-color: {P["ligne_alt"]};
        color: {P["texte"]};
        border: 1px solid {P["bordure"]};
        border-radius: 10px;
        gridline-color: {P["bordure"]};
        selection-background-color: {P["selection"]};
        selection-color: {P["texte"]};
        outline: none;
    }}

    QTableWidget::item,
    QTableView::item {{
        padding: 7px;
        border: none;
    }}

    QHeaderView::section {{
        background-color: {P["entete_bg"]};
        color: {P["entete_txt"]};
        border: none;
        border-bottom: 1px solid {P["bordure"]};
        padding: 10px 8px;
        font-weight: 700;
    }}

    QTableCornerButton::section {{
        background-color: {P["entete_bg"]};
        border: none;
    }}

    /* ONGLETS */

    QTabWidget::pane {{
        background-color: {P["fond"]};
        border: 1px solid {P["bordure"]};
        border-radius: 10px;
        top: -1px;
    }}

    QTabBar::tab {{
        background-color: {P["sec_bg"]};
        color: {P["doux"]};
        border: 1px solid {P["bordure"]};
        border-bottom: none;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        padding: 10px 18px;
        margin-right: 4px;
        min-width: 90px;
    }}

    QTabBar::tab:hover {{
        background-color: {P["sec_hover"]};
        color: {P["texte"]};
    }}

    QTabBar::tab:selected {{
        background-color: {P["carte"]};
        color: {P["primaire"]};
        font-weight: 700;
        border-bottom: 3px solid {P["serie1"]};
    }}

    /* BARRE LATÉRALE */

    QWidget#sidebar,
    QFrame#sidebar {{
        background-color: {P["sidebar"]};
        color: {P["sidebar_txt"]};
        border: none;
    }}

    QLabel#logo {{
        color: {P["sidebar_txt"]};
        font-size: 17px;
        font-weight: 800;
        padding: 16px 14px 4px 14px;
    }}

    QLabel#logoSub {{
        color: {P["sidebar_doux"]};
        font-size: 10px;
        padding: 0 14px 16px 14px;
    }}

    QListWidget#menu {{
        background-color: {P["sidebar"]};
        color: {P["sidebar_txt"]};
        border: none;
        outline: none;
        padding: 4px 8px;
    }}

    QListWidget#menu::item {{
        color: {P["sidebar_txt"]};
        padding: 10px 10px;
        margin: 2px 0;
        border-radius: 7px;
        border-left: 3px solid transparent;
    }}

    QListWidget#menu::item:hover {{
        background-color: {P["sidebar_hover"]};
    }}

    QListWidget#menu::item:selected {{
        background-color: {P["sidebar_actif"]};
        color: #FFFFFF;
        font-weight: 700;
        border-left: 3px solid {P["serie1"]};
    }}

    QListWidget#menu::item:disabled {{
        background-color: transparent;
        color: {P["sidebar_doux"]};
        font-size: 9px;
        font-weight: 700;
        padding-top: 8px;
        padding-bottom: 5px;
    }}

    QFrame#sidePied {{
        background-color: {P["sidebar"]};
        border-top: 1px solid {P["sep_side"]};
    }}

    QLabel#utilisateur {{
        color: {P["sidebar_txt"]};
        font-size: 12px;
        font-weight: 700;
        padding: 4px 12px;
    }}

    QLabel#role {{
        color: {P["sidebar_doux"]};
        font-size: 10px;
        padding: 0 12px 10px 12px;
    }}

    QFrame#sepSection {{
        background-color: {P["sep_side"]};
        border: none;
    }}

    /* BARRES DE DÉFILEMENT */

    QScrollArea {{
        background-color: transparent;
        border: none;
    }}

    QScrollBar:vertical {{
        background-color: transparent;
        width: 10px;
        margin: 3px;
        border: none;
    }}

    QScrollBar::handle:vertical {{
        background-color: {P["bordure"]};
        border-radius: 4px;
        min-height: 28px;
    }}

    QScrollBar::handle:vertical:hover {{
        background-color: {P["doux"]};
    }}

    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0;
        border: none;
    }}

    QScrollBar:horizontal {{
        background-color: transparent;
        height: 10px;
        margin: 3px;
        border: none;
    }}

    QScrollBar::handle:horizontal {{
        background-color: {P["bordure"]};
        border-radius: 4px;
        min-width: 28px;
    }}

    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {{
        width: 0;
        border: none;
    }}

    /* BARRES DE PROGRESSION */

    QProgressBar {{
        background-color: {P["sec_bg"]};
        color: {P["texte"]};
        border: 1px solid {P["bordure"]};
        border-radius: 6px;
        text-align: center;
        min-height: 12px;
    }}

    QProgressBar::chunk {{
        background-color: {P["serie1"]};
        border-radius: 5px;
    }}

    /* CASES ET BOUTONS RADIO */

    QCheckBox,
    QRadioButton {{
        color: {P["texte"]};
        spacing: 8px;
        background-color: transparent;
    }}

    /* INFOBULLES ET MENUS */

    QToolTip {{
        background-color: {P["titre"]};
        color: #FFFFFF;
        border: 1px solid {P["bordure"]};
        border-radius: 5px;
        padding: 6px 8px;
    }}

    QMenu {{
        background-color: {P["carte"]};
        color: {P["texte"]};
        border: 1px solid {P["bordure"]};
        padding: 5px;
    }}

    QMenu::item {{
        padding: 8px 22px;
        border-radius: 4px;
    }}

    QMenu::item:selected {{
        background-color: {P["selection"]};
        color: {P["texte"]};
    }}

    /* ALERTES */

    QLabel#alerteNeutre {{
        background-color: {P["neutre_bg"]};
        color: {P["neutre_txt"]};
        border: 1px solid {P["neutre_bordure"]};
        border-radius: 8px;
        padding: 10px;
    }}

    QLabel#alertePositive {{
        background-color: {P["positif_bg"]};
        color: {P["positif_txt"]};
        border: 1px solid {P["positif_bordure"]};
        border-radius: 8px;
        padding: 10px;
    }}

    QLabel#alerteRisque {{
        background-color: {P["risque_bg"]};
        color: {P["risque_txt"]};
        border: 1px solid {P["risque_bordure"]};
        border-radius: 8px;
        padding: 10px;
    }}

    QLabel#alerteAmbre {{
        background-color: {P["ambre_bg"]};
        color: {P["ambre_txt"]};
        border: 1px solid {P["ambre_bordure"]};
        border-radius: 8px;
        padding: 10px;
    }}

    /* BADGES */

    QLabel[badge="vert"] {{
        background-color: {P["positif_bg"]};
        color: {P["positif_txt"]};
        border: 1px solid {P["positif_bordure"]};
        border-radius: 7px;
        padding: 4px 8px;
        font-weight: 700;
    }}

    QLabel[badge="rouge"] {{
        background-color: {P["risque_bg"]};
        color: {P["risque_txt"]};
        border: 1px solid {P["risque_bordure"]};
        border-radius: 7px;
        padding: 4px 8px;
        font-weight: 700;
    }}

    QLabel[badge="ambre"] {{
        background-color: {P["ambre_bg"]};
        color: {P["ambre_txt"]};
        border: 1px solid {P["ambre_bordure"]};
        border-radius: 7px;
        padding: 4px 8px;
        font-weight: 700;
    }}

    QLabel[badge="gris"] {{
        background-color: {P["sec_bg"]};
        color: {P["doux"]};
        border: 1px solid {P["bordure"]};
        border-radius: 7px;
        padding: 4px 8px;
        font-weight: 700;
    }}

    /* SÉPARATEURS */

    QFrame[frameShape="4"],
    QFrame[frameShape="5"] {{
        color: {P["bordure"]};
        background-color: {P["bordure"]};
        border: none;
    }}

    /* BOÎTES DE DIALOGUE */

    QMessageBox {{
        background-color: {P["carte"]};
    }}

    QMessageBox QLabel {{
        color: {P["texte"]};
        background-color: transparent;
    }}
    """


# ============================================================
# 7. APPLICATION DU THÈME
# ============================================================

def appliquer_theme(app=None, mode=None):
    """
    Applique le thème à l'application.

    Si aucun mode n'est fourni, le mode sauvegardé est chargé.
    """
    if app is None:
        app = QApplication.instance()

    if app is None:
        raise RuntimeError(
            "Aucune instance QApplication n'est disponible."
        )

    mode_actif = mode if mode is not None else charger_mode()

    definir_mode(mode_actif)

    app.setStyle("Fusion")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(construire_qss())

    pg.setConfigOptions(
        antialias=True,
        background=P["carte"],
        foreground=P["texte"],
    )

    return P


# ============================================================
# 8. CHANGEMENT DE THÈME
# ============================================================

def changer_theme(app, mode, sauvegarder=True):
    """Change le thème à l'exécution."""
    appliquer_theme(app, mode)

    if sauvegarder:
        enregistrer_mode(mode)

    return P


# ============================================================
# 9. STYLE DES GRAPHIQUES PYQTGRAPH
# ============================================================

def styler_graphique(graphique, titre=None):
    """Applique le style actif à un PlotWidget."""
    graphique.setBackground(P["carte"])
    graphique.setMenuEnabled(False)
    graphique.showGrid(x=False, y=True, alpha=0.20)
    graphique.setContentsMargins(5, 5, 5, 5)

    for nom in ("left", "bottom"):
        axe = graphique.getAxis(nom)
        axe.setPen(P["grille"])
        axe.setTextPen(P["doux"])
        axe.setStyle(
            tickFont=QFont("Segoe UI", 9)
        )

    if titre:
        graphique.setTitle(
            titre,
            color=P["texte"],
            size="12pt",
        )

    return graphique


# ============================================================
# 10. OUTILS DE COULEUR POUR LES GRAPHIQUES
# ============================================================

def couleur_serie(numero=1):
    """Retourne une couleur parmi les trois couleurs de série."""
    couleurs = {
        1: P["serie1"],
        2: P["serie2"],
        3: P["serie3"],
    }

    return couleurs.get(numero, P["serie1"])


def couleur_avec_alpha(couleur, alpha=80):
    """Retourne un QColor avec un niveau de transparence."""
    resultat = QColor(couleur)
    resultat.setAlpha(max(0, min(255, int(alpha))))
    return resultat
