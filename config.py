"""
Configuration globale — constantes, coordonnées, destinataires.
"""

import os

APP_TITLE      = "Radar de Survol Aerien"
VERSION        = "v2.0"
LAT            = 48.9897
LON            = 2.0939
DELTA          = 0.027
SCAN_INTERVAL  = 60
DEDUP_WINDOW   = 600
DB_FILE        = os.path.join(os.path.expanduser("~"), "survols_conflans.db")
DESKTOP        = os.path.join(os.path.expanduser("~"), "Desktop")
OPENSKY_URL    = (f"https://opensky-network.org/api/states/all"
                  f"?lamin={LAT-DELTA}&lomin={LON-DELTA}"
                  f"&lamax={LAT+DELTA}&lomax={LON+DELTA}")
GEO_API        = "https://geo.api.gouv.fr/communes?codePostal={cp}&fields=nom&format=json"
GEO_API_CENTRE = "https://geo.api.gouv.fr/communes?codePostal={cp}&nom={nom}&fields=nom,centre&format=json"

ALT_MIN_LEGALE = 1000
HEURE_NUIT_DEB = 22
HEURE_NUIT_FIN = 6

TAG_NORMAL_LOW    = "normal_low"
TAG_NORMAL_MID    = "normal_mid"
TAG_NORMAL_HIGH   = "normal_high"
TAG_NORMAL_GROUND = "normal_ground"
TAG_INFR_ALT      = "infr_alt"
TAG_INFR_NUIT     = "infr_nuit"
TAG_INFR_DOUBLE   = "infr_double"

# Destinataires disponibles pour la plainte
DESTINATAIRES = [
    {
        "label": "ACNUSA",
        "nom":   "Autorite de Controle des Nuisances Sonores Aeroportuaires (ACNUSA)",
        "adresse": "244 Bd Saint-Germain",
        "cp_ville": "75007 PARIS",
    },
    {
        "label": "Maison de l'Environnement Roissy CDG",
        "nom":   "Maison de l'Environnement Roissy Charles de Gaulle",
        "adresse": "1, rue de France - BP 81007",
        "cp_ville": "95931 Roissy Charles de Gaulle Cedex",
    },
    {
        "label": "Ministre de la Transition ecologique",
        "nom":   "Monsieur le Ministre de la Transition ecologique",
        "adresse": "Hotel de Roquelaure - 246, Boulevard Saint-Germain",
        "cp_ville": "75007 PARIS",
    },
    {
        "label": "Mairie de ma commune",
        "nom":   None,   # Rempli dynamiquement depuis le profil
        "adresse": None,
        "cp_ville": None,
    },
]
