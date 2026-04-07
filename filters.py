"""
Filtrage des aéronefs et analyse réglementaire des infractions.
"""

import re
import config

# Types OACI des avions de transport commercial.
# Si hexdb.io identifie un appareil dont le type N'EST PAS dans cette liste,
# il est exclu de l'enregistrement.
TRANSPORT_TYPES = {
    # Airbus narrow
    "A318", "A319", "A320", "A321",
    # Airbus wide
    "A330",                              # hexdb : "A330 243" etc.
    "A332", "A333", "A338", "A339",
    "A340",                              # hexdb : "A340 313" etc.
    "A342", "A343", "A345", "A346",
    "A350",                              # hexdb : "A350 941" etc.
    "A359", "A35K",
    "A380",                              # hexdb : "A380 841" etc.
    "A388",
    # A220 (ex C-Series Bombardier)
    "A220",                              # hexdb : "A220 100/300"
    "BCS1", "BCS3",
    # Boeing narrow (737 NG + MAX)
    "B737",                              # hexdb : "B737 8" etc.
    "B732", "B733", "B734", "B735", "B736", "B738", "B739",
    "B37M", "B38M", "B39M",
    "737MAX",                            # hexdb : "737MAX 8/9/10"
    "737NG",                             # hexdb : "737NG 800/W" etc.
    # Boeing wide
    "B747",                              # hexdb : "B747 400" etc.
    "B744", "B748",
    "B757",                              # hexdb : "B757 200" etc.
    "B752", "B753",
    "B767",                              # hexdb : "B767 300" etc.
    "B762", "B763", "B764",
    "B777",                              # hexdb : "B777 3" etc.
    "777",                               # hexdb : "777 F" (cargo)
    "B772", "B773", "B77L", "B77W",
    "B778", "B779",
    "B787",                              # hexdb : "B787 8/9/10" etc.
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
    """Retourne True si le code type OACI correspond à un avion de transport commercial.
    hexdb.io retourne parfois des variantes longues (ex. 'A320 214') — on tronque
    au premier espace pour ne garder que le code de base ('A320')."""
    code = (type_code or "").upper().split()[0] if type_code else ""
    return code in TRANSPORT_TYPES


# Format standard OACI d'un vol commercial :
#   - exactement 3 lettres (code désignateur compagnie, ex. AFR, EZY, DLH)
#   - suivi de 1 à 4 chiffres (numéro de vol)
#   - optionnellement 1 lettre suffixe (variante de rotation, ex. AFR1234B)
# Les immatriculations de jets privés (F-ABCD, N123AB, D-ABCD…) ne correspondent
# jamais à ce format car elles contiennent un tiret ou ne commencent pas par
# exactement 3 lettres suivies de chiffres.
_CALLSIGN_RE = re.compile(r'^[A-Z]{3}[0-9]{1,4}[A-Z]?$')

# Catégories ADS-B à exclure explicitement :
#   A1 = aéronef léger, A2 = petit aéronef, A7 = hélicoptère
#   B1 = planeur, B2 = aérostat, B3 = parachutiste, B4 = ULM
_CAT_EXCLUES = {"A1", "A2", "A7", "B1", "B2", "B3", "B4"}


def est_avion_de_ligne(indicatif, vitesse_kmh, categorie=None):
    """
    Retourne True si l'aéronef est probablement un vol commercial.
    Couche 1 — indicatif : doit correspondre au format OACI compagnie strict.
    Couche 2 — vitesse   : > 200 km/h (avion de ligne en approche ≥ 220 km/h).
    Couche 3 — catégorie : exclut explicitement légers, hélicos, ULM, planeurs.
    """
    cs = (indicatif or "").strip().upper()

    if not cs or cs == "-":
        return False

    if not _CALLSIGN_RE.match(cs):
        return False

    if vitesse_kmh is not None and vitesse_kmh < 150:
        return False

    if categorie is not None and categorie in _CAT_EXCLUES:
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
