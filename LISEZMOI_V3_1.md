# Version 3.1 — perspectives intégrées au projet

Par rapport à la v3, cette version ajoute (aucune migration SQL nécessaire, aucune nouvelle dépendance) :

| Perspective | Où la trouver | Fichiers |
| --- | --- | --- |
| Évaluation régulière des prévisions | Menu Intelligence > « Suivi des prévisions » | `ml/backtest.py`, `ml/modeles.py`, `app/ui/evaluation_modeles.py` |
| Anomalies + règles de contrôle métier | Menu Intelligence > « Anomalies » (niveau + explication) | `ml/anomalies.py`, `app/ui/anomalies.py` |
| Segmentation enrichie (6 variables, agent identifié par nom + agence) | Menu Intelligence > « Segmentation agents » | `ml/segmentation.py`, `app/ui/segmentation.py` |
| Filtre avancé par catégorie de produit | Tableau de bord | `app/ui/dashboard.py` |
| Rapports personnalisables | Menu Administration > « Rapports » | `reports/generate_excel.py`, `app/ui/rapports.py` |
| Assistant qui explique les modèles | Menu Intelligence > « Assistant IA » | `app/ui/assistant_ia.py` |

Correctif : la prévision d'une agence n'utilise plus les mois précédant sa première vente (`ml/series.py`).

Tests : `pytest tests -v` (les fichiers `test_normalisation.py`, `test_v3.py` et `test_perspectives.py` n'ont pas besoin de PostgreSQL).

## Version 3.2 — tableau de bord et courbes refaits

- `app/ui/dashboard.py` : graphique d'évolution à 3 modes (Par agence, Total et tendance, Cumulé), classement des agences face à leur objectif, variation mensuelle du CA, répartition par catégorie.
- `app/ui/graphiques.py` : courbes lissées (interpolation PCHIP, sans dépassement), bulle d'informations au survol, légende cliquable.
- `app/calculs_dashboard.py` : calculs des graphiques (moyenne mobile, variation, cumul, pic/creux, parts), testés dans `tests/test_calculs_dashboard.py`.
- Bulle au survol ajoutée aux écrans Prévision, Scénarios et Suivi des prévisions.

## Version 3.3 — simulations

Nouvel écran **Intelligence > « 🧪 Simulations »** (à côté de « Scénarios »), en trois onglets :

| Onglet | Ce qu'il simule | Fichiers |
| --- | --- | --- |
| Marge | Effet d'une variation de prix ou de volume sur la marge, et baisse de prix qui annule la marge unitaire | `ml/simulations.py` (`simuler_marge`) |
| Performance d'un agent | Effet d'une hausse ou baisse de la performance d'un agent sur le CA de son agence et sur son objectif | `ml/simulations.py` (`simuler_agent`, `historique_mensuel_par_agent`, `objectifs_agents`) |
| Risque | Fourchette probable du CA cumulé (10 000 tirages Monte Carlo), probabilité d'atteindre l'objectif | `ml/simulations.py` (`simuler_risque`) |

Interface : `app/ui/simulations.py`, branchée dans `app/main_window.py`. Aucune migration SQL, aucune nouvelle dépendance.

Points à connaître :
- Le taux de marge n'est pas enregistré dans la base (les colonnes `prix` et `marge` de `dim_produit` sont à 0 à l'import). Il se saisit à l'écran ; la base n'est pas modifiée.
- La simulation de risque suppose des mois indépendants et ne modélise pas de tendance : c'est une fourchette, pas une prévision.
- La simulation d'agent utilise le rythme des 3 derniers mois de chaque agent.

Tests : `pytest tests/test_simulations.py -v` (21 tests, sans PostgreSQL).

## Version 3.4 — refonte de l'interface

Améliorations visuelles sans migration SQL ni nouvelle dépendance.

### `app/theme.py`
- **Palettes** : couleurs de fond légèrement adoucies (LIGHT : `#EFF4F4`, DARK : `#0B1518`), sidebar plus profonde, nouvelle clé `sep_side` (séparateur translucide) et `ambre_*` (alerte intermédiaire), `menu_sel_bg` et `menu_hover_bg` en `rgba`.
- **QSS** : bordures de focus sur les inputs (1.5 px), handle des sliders avec bordure blanche (look "thumb"), bouton avec micro-effet au clic (`padding` décalé), checkboxes stylisées, `QGroupBox`, `QToolTip` arrondi, ascenseurs plus fins (8 px), `QTabBar` avec fond actif sur l'onglet sélectionné, `QTabBar::tab:hover` avec fond doux, nouveaux sélecteurs `QFrame#sidePied`, `QLabel#bandeauDate`, `QLabel#bandeauRole`, `QLabel#sideSection`, `QFrame#sepSection`, `QLabel#alerteAmbre`.
- **`styler_graphique`** : opacité de la grille réduite à 0.20, `setContentsMargins(4,4,4,4)` pour éviter le recadrage des axes.

### `app/ui/widgets.py`
- **`BandeauAccueil`** : accepte deux nouveaux arguments (`date_texte`, `role`) et affiche la date et le badge de rôle dans la colonne droite du bandeau.
- **`CarteKPI`** : valeur en taille adaptative (18 px si le texte dépasse 200 px de large), `sous_texte` en `wordWrap`, `SizePolicy` `Expanding`.
- **`alerte(texte, type_)`** : nouvelle fonction qui retourne un `QLabel` d'alerte avec icône intégrée (`ℹ️ ⚠️ ✅ 🔔`). Remplace les `QLabel#alerteNeutre` nus dans les nouveaux écrans.
- **`separateur_h()`** : fine ligne horizontale pour structurer les formulaires longs.
- `ombre()` : ombre plus fine (flou 20, décalage 3) et adaptée au mode courant.

### `app/main_window.py`
- Sidebar élargie à 256 px (`setMinimumWidth(220)`), `setMinimumSize(900, 600)` sur la fenêtre.
- Pied de sidebar dans un `QFrame#sidePied` (fond semi-transparent + bordure haute).
- Les séparateurs de section utilisent désormais `None` dans `MENU` (au lieu de `("section", …)`) : le rendu est plus propre (libellé de section moins intrusif, espacements cohérents).
- Bouton de déconnexion avec icône ⏻.
- Marges de la zone de contenu harmonisées (28 / 22 / 28 / 20 px).

### `app/ui/dashboard.py`
- `BandeauAccueil` enrichi avec la date du jour et le rôle de l'utilisateur connecté.
