"""
Appels à l'API geo.api.gouv.fr — autocomplétion commune et récupération des coordonnées.
"""

import urllib.parse
import requests

from config import GEO_API, GEO_API_CENTRE, LAT, LON


def chercher_communes(code_postal):
    """Retourne la liste des noms de communes pour un code postal."""
    try:
        r = requests.get(GEO_API.format(cp=code_postal.strip()), timeout=5)
        if r.status_code == 200:
            return sorted([c["nom"] for c in r.json() if "nom" in c])
    except Exception:
        pass
    return []


def chercher_coordonnees_commune(code_postal, nom_commune):
    """Retourne (lat, lon) du centre de la commune, ou (LAT, LON) par défaut."""
    try:
        url = GEO_API_CENTRE.format(
            cp=code_postal.strip(),
            nom=urllib.parse.quote(nom_commune.strip()))
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            for c in data:
                if c.get("centre", {}).get("coordinates"):
                    lon_c, lat_c = c["centre"]["coordinates"]
                    return float(lat_c), float(lon_c)
    except Exception:
        pass
    return LAT, LON
