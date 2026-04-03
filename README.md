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

---

## Téléchargement direct (recommandé pour les débutants)

Pas besoin de Python ni de ligne de commande :

1. Allez dans [**Releases**](https://github.com/dcoldefy/survalerte/releases/latest)
2. Téléchargez **SurvAlerte.exe**
3. Double-cliquez sur le fichier pour lancer l'application

> Si Windows affiche un avertissement "application inconnue", cliquez sur **"Informations complémentaires"** puis **"Exécuter quand même"**.

---

## Installation avec Python (utilisateurs avancés)

### Prérequis

- [Python 3.8+](https://www.python.org/downloads/) — cochez **"Add Python to PATH"** lors de l'installation

### Étapes

**1. Ouvrir une fenêtre de commande**

- Appuyez sur les touches `Windows` + `R`
- Tapez `cmd` puis appuyez sur `Entrée`

**2. Copier-coller ces commandes une par une :**

```bash
git clone https://github.com/dcoldefy/survalerte.git
cd survalerte
pip install requests reportlab
python main.py
```

Au premier lancement, l'application demande de renseigner votre profil (nom, adresse, code postal, commune). Ces informations servent à personnaliser les plaintes PDF et à identifier votre commune de survol.

---

## Compiler le .exe soi-même

```bash
pip install pyinstaller
build.bat
```

L'exécutable est généré dans `dist/RadarSurvolConflans.exe`.

---

## Données

- Base SQLite : `~/survols_conflans.db`
- PDFs et CSV exportés sur le Bureau

## Version

v1.9 — David Coldefy avec Claude
