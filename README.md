# SurvAlerte — Radar de Survol Aérien

Application Windows de surveillance des survols aériens au-dessus de votre commune. Détecte les infractions réglementaires (altitude, horaires nocturnes) et génère des plaintes en PDF.

## Fonctionnalités

- Scan automatique toutes les 60 secondes via l'API OpenSky Network
- Filtrage des avions de ligne (exclusion ULM, hélicoptères, planeurs)
- Détection d'infractions : altitude < 1 000 m, survol nocturne (22h–6h), ou les deux
- Historique persistant en base SQLite
- Génération de plaintes PDF au format A4 (ReportLab)
- Export CSV de l'historique
- Interface graphique Tkinter avec tableau coloré et filtres

## Installation

### Prérequis

- [Python 3.8+](https://www.python.org/downloads/) — cochez "Add Python to PATH" lors de l'installation

### Étapes

```bash
git clone https://github.com/dcoldefy/survalerte.git
cd survalerte
pip install requests reportlab
python main.py
```

Au premier lancement, l'application demande de renseigner votre profil (nom, adresse, code postal, commune). Ces informations servent à personnaliser les plaintes PDF et à identifier votre commune de survol.

## Compiler en .exe (Windows)

Pour créer un exécutable autonome sans avoir besoin de Python :

```bash
pip install pyinstaller
build.bat
```

L'exécutable est généré dans `dist/RadarSurvolConflans.exe`.

## Zone surveillée

La zone de surveillance est centrée sur votre commune (configurée au premier lancement), avec un rayon ajustable depuis l'interface.

## Données

- Base SQLite : `~/survols_conflans.db`
- PDFs et CSV exportés sur le Bureau

## Version

v1.9 — David Coldefy avec Claude
