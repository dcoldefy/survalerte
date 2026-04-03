# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commandes essentielles

```bash
# Lancer l'application
python main.py

# Installer les dépendances
pip install -r requirements.txt

# Compiler en .exe Windows
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name "SurvAlerte" main.py
# → dist/SurvAlerte.exe
```

## Architecture modulaire

L'application est découpée en modules indépendants :

| Module | Rôle |
|---|---|
| `config.py` | Constantes globales, coordonnées GPS, intervalles, tags couleur, liste `DESTINATAIRES` |
| `database.py` | SQLite — `init_db`, `load_all`, `save_passage`, `load_profil`, `save_profil`, `clear_db` |
| `api.py` | Appels `geo.api.gouv.fr` — autocomplétion commune et géocodage centre de commune |
| `filters.py` | `est_avion_de_ligne()` (exclut ULM/hélicos/planeurs) et `analyser_infraction()` |
| `pdf.py` | `generer_plainte_pdf()` — lettre A4 via ReportLab |
| `utils.py` | Formatage (`fmt_alt`, `fmt_pays`…), distance Haversine, helpers `get_tag`/`get_code` |
| `dialogs.py` | `DialogueDestinataire`, `DialogueProfil`, `MenuContextuel` (Tkinter) |
| `app.py` | Classe `RadarApp` — fenêtre principale, boucle de scan, tableau, filtres, stats |
| `main.py` | Point d'entrée uniquement (`RadarApp().mainloop()`) |

## Flux de données

1. `RadarApp._scan_loop()` interroge **OpenSky Network** toutes les 60 s (thread daemon)
2. Chaque état ADS-B passe par `est_avion_de_ligne()` puis `analyser_infraction()`
3. Les passages retenus sont écrits dans **SQLite** (`~/survols_conflans.db`)
4. L'UI se rafraîchit via `_refresh_table()` + `_update_stats()`
5. Clic droit → `MenuContextuel` → `generer_plainte_pdf()` → PDF sur le Bureau

## Données persistantes

- **SQLite** : `~/survols_conflans.db` (tables `survols` + `profil`)
- **PDFs** et **CSV** exportés sur `~/Desktop/`
- Pas de fichier de configuration séparé — tout est dans `config.py`

## Zone surveillée et infractions

- Centre par défaut : `LAT=48.9897, LON=2.0939` (Conflans-Sainte-Honorine), recalculé dynamiquement depuis le profil utilisateur via `api.chercher_coordonnees_commune()`
- Rayon configurable dans l'UI (Spinbox km), converti en degrés (`km / 111.0`)
- Infractions : `ALT` (< 1 000 m), `NUIT` (22 h–6 h), `ALT+NUIT` (cumul)

## Dépendances

- **stdlib** : `tkinter`, `sqlite3`, `threading`, `csv`, `os`, `time`, `webbrowser`, `datetime`, `math`
- **pip** : `requests`, `reportlab` (voir `requirements.txt`)
- **build** : `pyinstaller`
