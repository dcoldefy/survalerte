"""
Fonctions utilitaires — formatage, tags couleur, distance GPS, drapeaux pays.
"""

import math

from config import (TAG_NORMAL_LOW, TAG_NORMAL_MID, TAG_NORMAL_HIGH,
                    TAG_NORMAL_GROUND, TAG_INFR_ALT, TAG_INFR_NUIT, TAG_INFR_DOUBLE)


def distance_km(lat1, lon1, lat2, lon2):
    """Distance en km entre deux points GPS (formule de Haversine)."""
    if None in (lat1, lon1, lat2, lon2):
        return None
    R = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(d_lon / 2) ** 2)
    return R * 2 * math.asin(math.sqrt(a))


def fmt_alt(alt):
    return f"{alt:,} m".replace(",", " ") if alt is not None else "-"


def fmt_val(v, suffix=""):
    return f"{v}{suffix}" if v is not None else "-"


FLAG_MAP = {
    "France": "FR", "Germany": "DE", "United Kingdom": "GB",
    "Netherlands": "NL", "Spain": "ES", "United States": "US",
    "Italy": "IT", "Belgium": "BE", "Switzerland": "CH",
    "Portugal": "PT", "Ireland": "IE", "Turkey": "TR",
    "Norway": "NO", "Sweden": "SE", "Denmark": "DK",
    "Poland": "PL", "Austria": "AT", "Luxembourg": "LU", "Morocco": "MA",
}


def fmt_pays(c):
    code = FLAG_MAP.get(c, "")
    return f"[{code}] {c}" if code else (c or "-")


def get_tag(alt_m, au_sol, code):
    if code == "ALT+NUIT": return TAG_INFR_DOUBLE
    if code == "NUIT":     return TAG_INFR_NUIT
    if code == "ALT":      return TAG_INFR_ALT
    if au_sol or alt_m is None: return TAG_NORMAL_GROUND
    if alt_m < 1000:       return TAG_NORMAL_LOW
    if alt_m < 5000:       return TAG_NORMAL_MID
    return TAG_NORMAL_HIGH


def get_code(msg):
    if not msg:                return ""
    if "DOUBLE" in msg:        return "ALT+NUIT"
    if "minimum legal" in msg: return "ALT"
    if "restriction" in msg:   return "NUIT"
    return ""


def majuscules(texte):
    return texte.strip().upper() if texte else texte
