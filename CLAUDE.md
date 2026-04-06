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

| Module | Rôle |
|---|---|
| `config.py` | Constantes globales, coordonnées GPS, intervalles, tags couleur, liste `DESTINATAIRES`. Certaines valeurs (`ALT_MIN_LEGALE`, `HEURE_NUIT_DEB`, `HEURE_NUIT_FIN`) sont **mutées à l'exécution** par `DialogueReglages`. |
| `database.py` | SQLite — `init_db`, `load_all`, `save_passage`, `load_profil`, `save_profil`, `clear_db`, `get_last_seen` |
| `api.py` | Appels `geo.api.gouv.fr` — autocomplétion commune et géocodage centre de commune |
| `filters.py` | `est_avion_de_ligne()` (exclut ULM/hélicos/planeurs) et `analyser_infraction()` |
| `pdf.py` | `generer_plainte_pdf()` et `generer_plainte_word()` — lettre A4 via ReportLab / python-docx |
| `utils.py` | Formatage (`fmt_alt`, `fmt_pays`…), distance Haversine, helpers `get_tag`/`get_code`, `majuscules` |
| `dialogs.py` | `DialogueDestinataire`, `DialogueProfil`, `DialogueReglages`, `MenuContextuel` (Tkinter) |
| `app.py` | Classe `RadarApp` — fenêtre principale, boucle de scan, tableau, filtres, stats, notifications Windows |
| `main.py` | Point d'entrée uniquement (`RadarApp().mainloop()`) |

## Flux de données

1. **Démarrage** : `__init__` → `_check_profil()` (profil obligatoire) → `_demander_reglages()` → `_demander_reinit()` (optionnel)
2. `RadarApp._scan_loop()` interroge **OpenSky Network** toutes les 60 s (thread daemon) — l'URL est reconstruite dynamiquement dans `_do_scan()` avec `scan_lat`/`scan_lon`
3. Chaque état ADS-B passe par `est_avion_de_ligne()` puis `analyser_infraction()`
4. Déduplication : `seen_recently` (dict en mémoire, fenêtre 10 min = `DEDUP_WINDOW`) évite les doublons entre scans
5. Les passages retenus sont écrits dans **SQLite** (`~/survols_conflans.db`)
6. L'UI se rafraîchit via `_refresh_table()` + `_update_stats()` (max 2 000 lignes affichées)
7. Infractions → notification toast Windows native via PowerShell (`_envoyer_notification` dans `app.py`)
8. Clic droit → `MenuContextuel` → sous-menu format (PDF / Word / les deux) → fichier(s) sur le Bureau

## Données persistantes

- **SQLite** : `~/survols_conflans.db` (tables `survols` + `profil`)
- `load_all()` retourne les survols triés par `altitude_m ASC` (les plus bas en premier)
- **PDFs** et **CSV** exportés sur `~/Desktop/`
- Pas de fichier de configuration séparé — tout est dans `config.py`

## Zone surveillée et infractions

- Centre recalculé dynamiquement depuis le profil utilisateur via `api.chercher_coordonnees_commune()` → stocké dans `RadarApp.scan_lat` / `scan_lon`
- Rayon configurable dans `DialogueReglages` (Spinbox km), converti en degrés dans `_do_scan()` : `delta = rayon_km / 111.0`
- Seuils modifiables au démarrage via `DialogueReglages` : altitude min, horaires nuit
- Infractions : `ALT` (< `ALT_MIN_LEGALE` m), `NUIT` (heure hors plage autorisée), `ALT+NUIT` (cumul)
- **Attention** : les filtres de l'UI détectent le type d'infraction par recherche de chaînes dans le champ `infraction` : `"minimum legal"`, `"restriction"`, `"DOUBLE"` — ne pas modifier ces mots-clés dans `filters.py` sans adapter `_apply_filters()` dans `app.py`

## Destinataires des plaintes

Définis dans `config.DESTINATAIRES`. L'entrée avec `"nom": None` correspond à la mairie de l'utilisateur, remplie dynamiquement depuis le profil dans `dialogs.py`. Ajouter un destinataire = ajouter un dict dans cette liste.

## Dépendances

- **stdlib** : `tkinter`, `sqlite3`, `threading`, `csv`, `os`, `time`, `webbrowser`, `datetime`, `math`, `subprocess`
- **pip** : `requests`, `reportlab`, `python-docx` (voir `requirements.txt`)
- **build** : `pyinstaller`
- Notifications Windows : PowerShell natif (aucune dépendance externe)
