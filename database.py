"""
Couche base de données SQLite — création, lecture, écriture des survols et du profil.
"""

import sqlite3
import time

from config import DB_FILE, DEDUP_WINDOW


def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS survols (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, heure TEXT, timestamp INTEGER,
        icao24 TEXT, indicatif TEXT,
        altitude_m INTEGER, altitude_geo INTEGER,
        vitesse_kmh INTEGER, cap_deg INTEGER,
        au_sol INTEGER, pays TEXT, lat REAL, lon REAL, infraction TEXT)""")
    try:
        c.execute("ALTER TABLE survols ADD COLUMN infraction TEXT")
    except Exception:
        pass
    c.execute("""CREATE TABLE IF NOT EXISTS profil (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        nom TEXT, prenom TEXT, adresse TEXT,
        code_postal TEXT, ville TEXT)""")
    try:
        c.execute("ALTER TABLE profil ADD COLUMN code_postal TEXT")
    except Exception:
        pass
    conn.commit()
    conn.close()


def load_profil():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    try:
        c.execute("SELECT nom, prenom, adresse, code_postal, ville FROM profil WHERE id=1")
        row = c.fetchone()
    except Exception:
        row = None
    conn.close()
    if row and row[0] and row[1] and row[4]:
        return {"nom": row[0], "prenom": row[1], "adresse": row[2] or "",
                "code_postal": row[3] or "", "ville": row[4]}
    return None


def save_profil(nom, prenom, adresse, code_postal, ville):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""INSERT INTO profil (id,nom,prenom,adresse,code_postal,ville)
        VALUES (1,?,?,?,?,?)
        ON CONFLICT(id) DO UPDATE SET nom=excluded.nom, prenom=excluded.prenom,
        adresse=excluded.adresse, code_postal=excluded.code_postal,
        ville=excluded.ville""",
        (nom, prenom, adresse, code_postal, ville))
    conn.commit()
    conn.close()


def save_passage(row):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""INSERT INTO survols
        (date,heure,timestamp,icao24,indicatif,altitude_m,altitude_geo,
         vitesse_kmh,cap_deg,au_sol,pays,lat,lon,infraction)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (row["date"], row["heure"], row["timestamp"], row["icao24"], row["indicatif"],
         row["altitude_m"], row["altitude_geo"], row["vitesse_kmh"], row["cap_deg"],
         row["au_sol"], row["pays"], row["lat"], row["lon"], row["infraction"]))
    conn.commit()
    conn.close()


def get_last_seen():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    cutoff = int(time.time()) - DEDUP_WINDOW
    c.execute("SELECT icao24, MAX(timestamp) FROM survols WHERE timestamp>=? GROUP BY icao24", (cutoff,))
    result = {r[0]: r[1] for r in c.fetchall()}
    conn.close()
    return result


def load_all():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""SELECT date,heure,timestamp,icao24,indicatif,altitude_m,altitude_geo,
                        vitesse_kmh,cap_deg,au_sol,pays,lat,lon,infraction
                 FROM survols ORDER BY altitude_m ASC""")
    rows = c.fetchall()
    conn.close()
    return rows


def clear_db():
    conn = sqlite3.connect(DB_FILE)
    conn.cursor().execute("DELETE FROM survols")
    conn.commit()
    conn.close()
