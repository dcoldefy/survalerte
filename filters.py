"""
Filtrage des aéronefs et analyse réglementaire des infractions.
"""

import config

# Types OACI des avions de transport commercial.
# Si hexdb.io identifie un appareil dont le type N'EST PAS dans cette liste,
# il est exclu de l'enregistrement.
TRANSPORT_TYPES = {
    # Airbus narrow
    "A318", "A319", "A320", "A321",
    # Airbus wide
    "A332", "A333", "A338", "A339",
    "A342", "A343", "A345", "A346",
    "A359", "A35K",
    "A388",
    # A220 (ex C-Series Bombardier)
    "BCS1", "BCS3",
    # Boeing narrow (737 NG + MAX)
    "B732", "B733", "B734", "B735", "B736", "B737", "B738", "B739",
    "B37M", "B38M", "B39M",
    # Boeing wide
    "B744", "B748",
    "B752", "B753",
    "B762", "B763", "B764",
    "B772", "B773", "B77L", "B77W",
    "B778", "B779",
    "B788", "B789", "B78X",
    # Embraer commercial (E-Jets v1 + v2)
    "E135", "E145", "E170", "E175", "E190", "E195", "E290", "E295",
    # Bombardier CRJ régional
    "CRJ2", "CRJ7", "CRJ9", "CRJX",
    # ATR
    "AT43", "AT45", "AT72", "AT75", "AT76",
    # Fokker
    "F70", "F100",
    # Dash 8 (Q-Series)
    "DH8A", "DH8B", "DH8C", "DH8D",
    # McDonnell Douglas / Boeing MD
    "MD11", "MD81", "MD82", "MD83", "MD88", "MD90",
    # COMAC / Sukhoi
    "C919", "SU95", "SU9B",
}


def est_transport_commercial(type_code):
    """Retourne True si le code type OACI correspond à un avion de transport commercial."""
    return (type_code or "").upper() in TRANSPORT_TYPES


def est_avion_de_ligne(indicatif, vitesse_kmh, categorie=None):
    """
    Retourne True si l'avion est probablement un avion de ligne commercial.
    Critères :
    1. Indicatif de 6-8 caractères commençant par 2-3 lettres (code OACI compagnie)
    2. Vitesse > 150 km/h
    3. Catégorie ADS-B A3/A4/A5 si disponible (gros porteurs)
    """
    cs = (indicatif or "").strip()

    if not cs or cs == "-":
        return False

    if len(cs) < 5:
        return False
    if cs[0].isdigit():
        return False

    lettres_debut = 0
    for ch in cs:
        if ch.isalpha():
            lettres_debut += 1
        else:
            break
    if lettres_debut < 2 or lettres_debut > 4:
        return False

    reste = cs[lettres_debut:]
    if not any(c.isdigit() for c in reste):
        return False

    if vitesse_kmh is not None and vitesse_kmh < 150:
        return False

    if categorie is not None:
        if categorie in ("A1", "A2", "B1", "B2", "B3", "B4", "C1", "C2", "C3"):
            return False

    return True


def analyser_infraction(alt_m, heure_str, au_sol):
    """
    Retourne (code_infraction, message_detail) ou (None, "").
    Codes : "ALT", "NUIT", "ALT+NUIT".
    """
    if au_sol:
        return None, ""
    infr_alt = (alt_m is not None and alt_m < config.ALT_MIN_LEGALE)
    try:
        hh = int(heure_str.split(":")[0])
        infr_nuit = (hh >= config.HEURE_NUIT_DEB or hh < config.HEURE_NUIT_FIN)
    except Exception:
        infr_nuit = False
    if infr_alt and infr_nuit:
        return "ALT+NUIT", (f"DOUBLE INFRACTION : altitude {alt_m} m sous le minimum legal"
            f" de {config.ALT_MIN_LEGALE} m ET vol a {heure_str} hors plage autorisee CDG"
            f" ({config.HEURE_NUIT_DEB}h-{config.HEURE_NUIT_FIN}h)")
    if infr_alt:
        return "ALT", (f"Altitude {alt_m} m inferieure au minimum legal"
            f" de {config.ALT_MIN_LEGALE} m (arrete 1957)")
    if infr_nuit:
        return "NUIT", (f"Vol a {heure_str} : restriction nocturne CDG"
            f" ({config.HEURE_NUIT_DEB}h-{config.HEURE_NUIT_FIN}h)")
    return None, ""
