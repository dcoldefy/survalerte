"""
Fenêtre principale RadarApp — boucle de scan, tableau, filtres, statistiques.
"""

import csv
import sqlite3
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

import subprocess

import requests


def _envoyer_notification(title: str, message: str) -> None:
    """Notification toast Windows native via PowerShell (sans dépendance externe)."""
    title_esc   = title.replace("'", "''")
    message_esc = message.replace("'", "''")
    script = (
        "[Windows.UI.Notifications.ToastNotificationManager,"
        " Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null;"
        "$t   = [Windows.UI.Notifications.ToastTemplateType]::ToastText02;"
        "$xml = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent($t);"
        "$nd  = $xml.GetElementsByTagName('text');"
        f"$nd[0].AppendChild($xml.CreateTextNode('{title_esc}'))   | Out-Null;"
        f"$nd[1].AppendChild($xml.CreateTextNode('{message_esc}')) | Out-Null;"
        "$toast = [Windows.UI.Notifications.ToastNotification]::new($xml);"
        "$app = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}"
        "\\WindowsPowerShell\\v1.0\\powershell.exe';"
        "[Windows.UI.Notifications.ToastNotificationManager]"
        "::CreateToastNotifier($app).Show($toast);"
    )
    try:
        subprocess.Popen(
            ["powershell", "-WindowStyle", "Hidden", "-NonInteractive", "-Command", script],
            creationflags=0x08000000,  # CREATE_NO_WINDOW
        )
    except Exception:
        pass

from config import (APP_TITLE, DB_FILE, DEDUP_WINDOW, LAT, LON,
                    SCAN_INTERVAL, VERSION,
                    TAG_NORMAL_LOW, TAG_NORMAL_MID, TAG_NORMAL_HIGH,
                    TAG_NORMAL_GROUND, TAG_INFR_ALT, TAG_INFR_NUIT, TAG_INFR_DOUBLE)
from api import chercher_coordonnees_commune
from database import clear_db, get_last_seen, init_db, load_all, save_passage
import config as _config
from dialogs import DialogueProfil, DialogueReglages, MenuContextuel
from filters import analyser_infraction, est_avion_de_ligne
from utils import distance_km, fmt_alt, fmt_pays, fmt_val, get_code, get_tag


class RadarApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title(f"{APP_TITLE}  {VERSION}")
        self.geometry("1200x720")
        self.minsize(950, 560)
        self.configure(bg="#F8F8F6")
        init_db()
        self.recording       = False
        self.recording_start = None
        self.stop_event    = threading.Event()
        self.next_scan_ts  = 0
        self.scan_count    = 0
        self.rows_cache    = []
        self.sort_col      = None
        self.sort_rev      = False
        self.seen_recently = get_last_seen()
        self.profil        = None
        self.rayon_km      = tk.IntVar(value=3)
        self.notif_active  = True
        self.scan_lat      = LAT
        self.scan_lon      = LON
        self._build_ui()
        self._refresh_table(load_all())
        self._update_stats()
        self._tick()
        self.after(100, self._check_profil)
        self.after(200, self._demander_reinit)

    # ---- Profil utilisateur --------------------------------------------------

    def _check_profil(self):
        from database import load_profil
        profil = load_profil()
        if profil:
            self.profil = profil
            self._afficher_profil()
            self._maj_coordonnees_profil()
        else:
            self._demander_profil(premier=True)
        self._demander_reglages()

    def _demander_reglages(self):
        dlg = DialogueReglages(self, rayon=self.rayon_km.get())
        self.wait_window(dlg)
        if dlg.result:
            self.rayon_km.set(dlg.result["rayon"])
            _config.ALT_MIN_LEGALE  = dlg.result["alt_min"]
            _config.HEURE_NUIT_DEB  = dlg.result["nuit_deb"]
            _config.HEURE_NUIT_FIN  = dlg.result["nuit_fin"]
            if hasattr(self, "_leg_alt_var"):
                self._leg_alt_var.set(f"Altitude < {_config.ALT_MIN_LEGALE} m")
                self._leg_nuit_var.set(f"Vol nocturne {_config.HEURE_NUIT_DEB}h-{_config.HEURE_NUIT_FIN}h")

    def _maj_coordonnees_profil(self):
        if not self.profil:
            return
        cp    = self.profil.get("code_postal", "")
        ville = self.profil.get("ville", "")
        if cp and ville:
            def fetch():
                lat, lon = chercher_coordonnees_commune(cp, ville)
                self.scan_lat = lat
                self.scan_lon = lon
            threading.Thread(target=fetch, daemon=True).start()

    def _demander_reinit(self):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM survols")
        nb = c.fetchone()[0]
        conn.close()
        if nb == 0:
            return
        reponse = messagebox.askyesno(
            "Réinitialiser les données",
            f"La base contient {nb} survol(s) enregistré(s).\n\n"
            "Voulez-vous vider les données au démarrage ?",
            icon="question")
        if reponse:
            clear_db()
            self.seen_recently = {}
            self._refresh_table([])
            self._update_stats()

    def _demander_profil(self, premier=False):
        titre = "Bienvenue - Premiere utilisation" if premier else "Modifier le profil"
        dlg = DialogueProfil(self, profil=self.profil if not premier else None, titre=titre)
        self.wait_window(dlg)
        if dlg.result:
            self.profil = dlg.result
            self._afficher_profil()
            self._maj_coordonnees_profil()
        elif premier:
            self._demander_profil(premier=True)

    def _afficher_profil(self):
        if self.profil:
            p = self.profil
            adresse_txt = f" - {p['adresse']}" if p.get("adresse") else ""
            cp_ville = f"{p.get('code_postal', '')} {p['ville']}".strip()
            self.lbl_profil.config(
                text=f"{p['prenom']} {p['nom']}{adresse_txt}, {cp_ville}")
            ville = p.get("ville", "")
            self.title(f"{APP_TITLE}{' - ' + ville if ville else ''}  {VERSION}")
            commune_txt = f"{ville}  |  " if ville else ""
            self.lbl_commune.config(text=f"{commune_txt}OpenSky Network  |  ADS-B")

    # ---- Construction de l'interface ----------------------------------------

    def _build_ui(self):
        top = tk.Frame(self, bg="#FFFFFF", pady=10, padx=16)
        top.pack(fill="x", side="top")
        tk.Label(top, text="Radar de Survol Aerien",
                 font=("Segoe UI", 14, "bold"), bg="#FFFFFF", fg="#1a1a1a").pack(side="left")
        self.lbl_commune = tk.Label(top, text="OpenSky Network  |  ADS-B",
                 font=("Segoe UI", 9), bg="#FFFFFF", fg="#888")
        self.lbl_commune.pack(side="left", padx=12)

        ubar = tk.Frame(self, bg="#E6F1FB", pady=6, padx=16)
        ubar.pack(fill="x")
        tk.Label(ubar, text="Utilisateur :", font=("Segoe UI", 8, "bold"),
                 bg="#E6F1FB", fg="#185FA5").pack(side="left")
        self.lbl_profil = tk.Label(ubar, text="(chargement...)",
                                   font=("Segoe UI", 8), bg="#E6F1FB", fg="#185FA5")
        self.lbl_profil.pack(side="left", padx=(6, 0))
        tk.Button(ubar, text="Changer de profil",
                  command=lambda: self._demander_profil(premier=False),
                  font=("Segoe UI", 8), bg="#B5D4F4", fg="#0C447C",
                  activebackground="#85B7EB", relief="flat",
                  padx=10, pady=2, cursor="hand2").pack(side="right")

        sf = tk.Frame(self, bg="#F8F8F6", padx=16, pady=8)
        sf.pack(fill="x")
        self.stat_vars = {}
        self.stat_labels = {}
        for key, label, color, default_val, font_size in [
            ("sDepuis",      "Enregistrements depuis :", "#1a1a1a", "-",  12),
            ("sTotal",       "Passages enregistres",     "#1a1a1a", "0",  16),
            ("sInfractions", "Infractions detectees",    "#2E7D32", "0",  16),
        ]:
            card = tk.Frame(sf, bg="#EFEFED", padx=14, pady=8)
            card.pack(side="left", expand=True, fill="x", padx=(0, 8))
            tk.Label(card, text=label, font=("Segoe UI", 8),
                     bg="#EFEFED", fg="#888").pack(anchor="w")
            var = tk.StringVar(value=default_val)
            self.stat_vars[key] = var
            lbl = tk.Label(card, textvariable=var, font=("Segoe UI", font_size, "bold"),
                           bg="#EFEFED", fg=color)
            lbl.pack(anchor="w")
            self.stat_labels[key] = lbl

        leg = tk.Frame(self, bg="#F8F8F6", padx=16, pady=3)
        leg.pack(fill="x")
        tk.Label(leg, text="Legende infractions : ", font=("Segoe UI", 8, "bold"),
                 bg="#F8F8F6", fg="#555").pack(side="left")
        self._leg_alt_var  = tk.StringVar(value=f"Altitude < {_config.ALT_MIN_LEGALE} m")
        self._leg_nuit_var = tk.StringVar(value=f"Vol nocturne {_config.HEURE_NUIT_DEB}h-{_config.HEURE_NUIT_FIN}h")
        for bg, fg, var_or_txt in [
            ("#FFCCCC", "#7B0000", self._leg_alt_var),
            ("#FFB3C1", "#7B0000", self._leg_nuit_var),
            ("#FF6B6B", "#FFFFFF", "Double infraction"),
        ]:
            fr = tk.Frame(leg, bg=bg, padx=6, pady=2)
            fr.pack(side="left", padx=(5, 0))
            if isinstance(var_or_txt, tk.StringVar):
                tk.Label(fr, textvariable=var_or_txt, font=("Segoe UI", 7), bg=bg, fg=fg).pack()
            else:
                tk.Label(fr, text=var_or_txt, font=("Segoe UI", 7), bg=bg, fg=fg).pack()

        af = tk.Frame(self, bg="#F8F8F6", padx=16, pady=4)
        af.pack(fill="x")
        self.btn_rec = tk.Button(af, text="Demarrer l'enregistrement",
                                  command=self._toggle_rec,
                                  font=("Segoe UI", 10, "bold"),
                                  bg="#1D9E75", fg="white",
                                  activebackground="#0F6E56",
                                  relief="flat", padx=16, pady=6, cursor="hand2")
        self.btn_rec.pack(side="left")
        for txt, cmd in [("Exporter CSV", self._export_csv),
                          ("Infractions seulement", self._show_infractions),
                          ("Effacer journal", self._clear)]:
            tk.Button(af, text=txt, command=cmd, font=("Segoe UI", 9),
                      bg="#E8E8E6", fg="#333", activebackground="#D8D8D6",
                      relief="flat", padx=12, pady=6,
                      cursor="hand2").pack(side="left", padx=(8, 0))
        self.btn_notif = tk.Button(af, text="Notifications : ON",
                                   command=self._toggle_notif,
                                   font=("Segoe UI", 9),
                                   bg="#1D9E75", fg="white",
                                   activebackground="#0F6E56",
                                   relief="flat", padx=12, pady=6,
                                   cursor="hand2")
        self.btn_notif.pack(side="left", padx=(8, 0))
        self.lbl_timer = tk.Label(af, text="", font=("Segoe UI", 9, "italic"),
                                   bg="#F8F8F6", fg="#999")
        self.lbl_timer.pack(side="left", padx=16)
        tk.Label(af, text="Rayon (km) :", font=("Segoe UI", 9),
                 bg="#F8F8F6", fg="#666").pack(side="left", padx=(8, 2))
        tk.Spinbox(af, from_=1, to=50, increment=1, width=4,
                   font=("Segoe UI", 9), textvariable=self.rayon_km,
                   relief="flat", bg="#E8E8E6").pack(side="left")

        ff = tk.Frame(self, bg="#F8F8F6", padx=16, pady=4)
        ff.pack(fill="x")

        def lbl(t):
            tk.Label(ff, text=t, font=("Segoe UI", 9),
                     bg="#F8F8F6", fg="#666").pack(side="left", padx=(0, 4))

        lbl("Jour :")
        self.filt_day = ttk.Combobox(ff, width=12, state="readonly", values=["Tous"])
        self.filt_day.current(0)
        self.filt_day.pack(side="left")
        self.filt_day.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())

        lbl("  Infractions :")
        self.filt_infr = ttk.Combobox(ff, width=20, state="readonly",
            values=["Tous les vols", "Infractions uniquement",
                    "Altitude < 1000 m", "Vols nocturnes", "Double infraction"])
        self.filt_infr.current(0)
        self.filt_infr.pack(side="left")
        self.filt_infr.bind("<<ComboboxSelected>>", lambda e: self._apply_filters())
        tk.Label(ff, text="   Clic droit sur un vol pour suivre ou deposer plainte",
                 font=("Segoe UI", 9), bg="#F8F8F6", fg="#1a1a1a").pack(side="left")

        tf = tk.Frame(self, bg="#F8F8F6", padx=16, pady=4)
        tf.pack(fill="both", expand=True)
        self._cols = ("Date", "Heure", "Indicatif", "ICAO24", "Altitude (m)",
                      "Vitesse (km/h)", "Cap", "Au sol", "Pays", "Distance (km)", "Statut reglementaire")
        self.tree = ttk.Treeview(tf, columns=self._cols, show="headings", selectmode="browse")
        for col, w in zip(self._cols, (88, 78, 95, 88, 105, 105, 60, 60, 155, 90, 195)):
            self.tree.heading(col, text=col, command=lambda c=col: self._sort_by(c))
            self.tree.column(col, width=w, minwidth=40)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#FFFFFF", fieldbackground="#FFFFFF",
                         rowheight=26, font=("Segoe UI", 9))
        style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"),
                         background="#EFEFED", relief="flat")
        style.map("Treeview", background=[("selected", "#D6EAF8")])
        self.tree.tag_configure(TAG_NORMAL_LOW,    background="#FFF0F0")
        self.tree.tag_configure(TAG_NORMAL_MID,    background="#FFFBF0")
        self.tree.tag_configure(TAG_NORMAL_HIGH,   background="#F0F4FF")
        self.tree.tag_configure(TAG_NORMAL_GROUND, background="#F5F5F5")
        self.tree.tag_configure(TAG_INFR_ALT,    background="#FFCCCC", foreground="#7B0000")
        self.tree.tag_configure(TAG_INFR_NUIT,   background="#FFB3C1", foreground="#7B0000")
        self.tree.tag_configure(TAG_INFR_DOUBLE, background="#FF6B6B", foreground="#FFFFFF")
        vsb = ttk.Scrollbar(tf, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        self.tooltip = tk.Label(self, text="", font=("Segoe UI", 8),
                                bg="#FFFFE0", fg="#333", relief="solid", bd=1,
                                padx=6, pady=3, wraplength=500, justify="left")
        self.tree.bind("<Motion>",   self._on_motion)
        self.tree.bind("<Leave>",    lambda e: self.tooltip.place_forget())
        self.tree.bind("<Button-3>", self._on_right_click)

        bot = tk.Frame(self, bg="#EFEFED", pady=4, padx=16)
        bot.pack(fill="x", side="bottom")
        self.lbl_foot = tk.Label(bot, text="", font=("Segoe UI", 8),
                                  bg="#EFEFED", fg="#888")
        self.lbl_foot.pack(side="left")
        tk.Label(bot, text=f"{APP_TITLE}  {VERSION}",
                 font=("Segoe UI", 8), bg="#EFEFED", fg="#bbb").pack(side="right")

    # ---- Interactions tableau ------------------------------------------------

    def _sort_by(self, col):
        if self.sort_col == col:
            self.sort_rev = not self.sort_rev
        else:
            self.sort_col = col
            self.sort_rev = False
        for c in self._cols:
            arrow = (" ▲" if not self.sort_rev else " ▼") if c == self.sort_col else ""
            self.tree.heading(c, text=c + arrow)
        self._apply_filters()

    def _on_right_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        self.tree.selection_set(item)
        vals = self.tree.item(item, "values")
        if not vals:
            return
        date = vals[0]; heure = vals[1]; icao24 = vals[3]; indicatif = vals[2]
        altitude_m = None
        for r in self.rows_cache:
            if r[0] == date and r[1] == heure and r[3] == icao24:
                altitude_m = r[5]
                break
        vol = {"date": date, "heure": heure, "indicatif": indicatif,
               "icao24": icao24, "altitude_m": altitude_m}
        menu = MenuContextuel(self, vol=vol, profil=self.profil)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _on_motion(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            self.tooltip.place_forget()
            return
        # Convertir en coordonnées relatives à la fenêtre principale
        wx = event.x_root - self.winfo_rootx() + 16
        wy = event.y_root - self.winfo_rooty() + 10
        vals = self.tree.item(item, "values")
        statut = vals[10] if len(vals) > 10 else ""
        if statut and statut != "-":
            icao = vals[3]; heure = vals[1]; msg = statut
            for r in self.rows_cache:
                if r[3] == icao and r[1] == heure and r[13]:
                    msg = r[13]
                    break
            msg += "\n\n→ Clic droit pour plus d'options"
            self.tooltip.config(text=msg)
            self.tooltip.place(x=wx, y=wy)
        else:
            self.tooltip.config(text="→ Clic droit pour plus d'options")
            self.tooltip.place(x=wx, y=wy)

    # ---- Enregistrement / scan ----------------------------------------------

    def _toggle_rec(self):
        if not self.recording:
            self.recording = True
            self.recording_start = datetime.now()
            self.stat_vars["sDepuis"].set(self.recording_start.strftime("%d/%m/%Y %H:%M"))
            self.stop_event.clear()
            self.btn_rec.config(text="Arreter l'enregistrement",
                                bg="#E24B4A", activebackground="#A32D2D")
            self._set_status("Enregistrement en cours", "#E8F8F0", "#0F6E56")
            threading.Thread(target=self._scan_loop, daemon=True).start()
        else:
            self.recording = False
            self.stop_event.set()
            self.btn_rec.config(text="Demarrer l'enregistrement",
                                bg="#1D9E75", activebackground="#0F6E56")
            self._set_status("En pause", "#FFF8E1", "#BA7517")
            self.lbl_timer.config(text="")

    def _scan_loop(self):
        while self.recording and not self.stop_event.is_set():
            self.next_scan_ts = time.time() + SCAN_INTERVAL
            self._do_scan()
            for _ in range(SCAN_INTERVAL * 10):
                if self.stop_event.is_set():
                    break
                time.sleep(0.1)

    def _do_scan(self):
        self.scan_count += 1
        self._set_status("Scan en cours...", "#E8F0FF", "#185FA5")
        try:
            delta = max(self.rayon_km.get(), 1) / 111.0
            lat, lon = self.scan_lat, self.scan_lon
            url = (f"https://opensky-network.org/api/states/all"
                   f"?lamin={lat-delta}&lomin={lon-delta}"
                   f"&lamax={lat+delta}&lomax={lon+delta}")
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            states = [s for s in (resp.json().get("states") or [])
                      if s[5] is not None and s[6] is not None]
            now = datetime.now(); now_ts = int(now.timestamp())
            date_s = now.strftime("%d/%m/%Y"); time_s = now.strftime("%H:%M:%S")
            added = 0; skipped = 0; filtres = 0; n_infr = 0

            for s in states:
                icao = (s[0] or "").strip()
                if not icao:
                    continue
                if now_ts - self.seen_recently.get(icao, 0) < DEDUP_WINDOW:
                    skipped += 1
                    continue

                alt_m     = int(s[7])      if s[7] is not None else None
                vitesse   = int(s[9] * 3.6) if s[9] is not None else None
                indicatif = (s[1] or "").strip() or "-"
                categorie = s[16] if len(s) > 16 else None
                au_sol    = 1 if s[8] else 0

                if au_sol or not est_avion_de_ligne(indicatif, vitesse, categorie):
                    filtres += 1
                    continue

                code_infr, msg_infr = analyser_infraction(alt_m, time_s, au_sol)
                if code_infr:
                    n_infr += 1

                row = {"date": date_s, "heure": time_s, "timestamp": now_ts,
                       "icao24": icao, "indicatif": indicatif,
                       "altitude_m": alt_m,
                       "altitude_geo": int(s[13]) if s[13] is not None else None,
                       "vitesse_kmh": vitesse,
                       "cap_deg": int(s[10]) if s[10] is not None else None,
                       "au_sol": au_sol, "pays": s[2] or "-",
                       "lat": s[6], "lon": s[5], "infraction": msg_infr}
                save_passage(row)
                self.seen_recently[icao] = now_ts
                added += 1

            cutoff = now_ts - DEDUP_WINDOW
            self.seen_recently = {k: v for k, v in self.seen_recently.items() if v >= cutoff}
            if n_infr and self.notif_active:
                msg = (f"{n_infr} infraction{'s' if n_infr > 1 else ''} "
                       f"détectée{'s' if n_infr > 1 else ''} dans la zone surveillée.")
                _envoyer_notification("SurvAlerte — Infraction détectée", msg)

            infr_txt = f", {n_infr} infraction(s)" if n_infr else ""
            self._set_status(
                f"Scan #{self.scan_count} : {len(states)} detecte(s), "
                f"{added} avion(s) de ligne{infr_txt}, "
                f"{filtres} petit(s) avion(s) ignore(s), {skipped} doublon(s)",
                "#E8F8F0", "#0F6E56")
            self.after(0, lambda: self._refresh_table(load_all()))
            self.after(0, self._update_stats)
        except Exception as e:
            self._set_status(f"Erreur : {e}", "#FFF0F0", "#A32D2D")

    # ---- Tableau et filtres -------------------------------------------------

    def _refresh_table(self, db_rows):
        self.rows_cache = db_rows
        self._update_day_filter()
        self._apply_filters()

    def _update_day_filter(self):
        days = sorted(set(r[0] for r in self.rows_cache))
        cur = self.filt_day.get()
        self.filt_day["values"] = ["Tous"] + days
        self.filt_day.set(cur if cur in days else "Tous")

    def _apply_filters(self):
        rows = list(self.rows_cache)
        day_f  = self.filt_day.get()
        infr_f = self.filt_infr.get()

        if day_f != "Tous":
            rows = [r for r in rows if r[0] == day_f]
        if infr_f == "Infractions uniquement":
            rows = [r for r in rows if r[13]]
        elif infr_f == "Altitude < 1000 m":
            rows = [r for r in rows if r[13] and "minimum legal" in r[13]]
        elif infr_f == "Vols nocturnes":
            rows = [r for r in rows if r[13] and "restriction" in r[13]]
        elif infr_f == "Double infraction":
            rows = [r for r in rows if r[13] and "DOUBLE" in r[13]]

        if self.sort_col:
            none_hi = -1 if self.sort_rev else 99999
            col_key = {
                "Date":                 lambda r: r[2],
                "Heure":                lambda r: r[2],
                "Indicatif":            lambda r: r[4] or "",
                "ICAO24":               lambda r: r[3] or "",
                "Altitude (m)":         lambda r: r[5] if r[5] is not None else none_hi,
                "Vitesse (km/h)":       lambda r: r[7] if r[7] is not None else none_hi,
                "Cap":                  lambda r: r[8] if r[8] is not None else none_hi,
                "Au sol":               lambda r: r[9],
                "Pays":                 lambda r: r[10] or "",
                "Distance (km)":        lambda r: distance_km(self.scan_lat, self.scan_lon, r[11], r[12]) or none_hi,
                "Statut reglementaire": lambda r: r[13] or "",
            }.get(self.sort_col)
            if col_key:
                rows.sort(key=col_key, reverse=self.sort_rev)

        self._populate_tree(rows)

    def _populate_tree(self, rows):
        self.tree.delete(*self.tree.get_children())
        for r in rows[:2000]:
            date, heure, ts, icao24, indicatif, alt_m, alt_geo, vitesse, cap, au_sol, pays, lat, lon, infraction = r
            code = get_code(infraction)
            tag  = get_tag(alt_m, au_sol, code)
            if infraction:
                if "DOUBLE" in infraction:    statut = "!! Double infraction"
                elif "minimum" in infraction: statut = "! Altitude illegale"
                else:                         statut = "! Vol nocturne"
            else:
                statut = "-"
            dist     = distance_km(self.scan_lat, self.scan_lon, lat, lon)
            dist_txt = f"{dist:.1f} km" if dist is not None else "-"
            self.tree.insert("", "end", tags=(tag,), values=(
                date, heure, indicatif, icao24, fmt_alt(alt_m),
                fmt_val(vitesse, " km/h"), fmt_val(cap, "deg"),
                "Oui" if au_sol else "Non", fmt_pays(pays), dist_txt, statut))
        total = len(rows)
        self.lbl_foot.config(text=f"{min(total, 2000)}/{total} passages  |  BDD : {DB_FILE}")

    # ---- Statistiques et actions --------------------------------------------

    def _update_stats(self):
        rows = self.rows_cache
        self.stat_vars["sTotal"].set(str(len(rows)))
        n_infr = sum(1 for r in rows if r[13])
        self.stat_vars["sInfractions"].set(str(n_infr))
        self.stat_labels["sInfractions"].config(fg="#C0392B" if n_infr else "#2E7D32")

    def _show_infractions(self):
        self.filt_infr.set("Infractions uniquement")
        self._apply_filters()

    def _export_csv(self):
        if not self.rows_cache:
            messagebox.showinfo("Export", "Aucune donnee a exporter.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv"), ("Tous", "*.*")],
            initialfile=f"survols_conflans_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            title="Enregistrer le journal CSV")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            if self.profil:
                p = self.profil
                cp_ville = f"{p.get('code_postal', '')} {p['ville']}".strip()
                w.writerow([f"Utilisateur : {p['prenom']} {p['nom']}",
                             f"Adresse : {p.get('adresse', '')} {cp_ville}"])
                w.writerow([])
            w.writerow(["Date", "Heure", "Indicatif", "ICAO24", "Altitude_baro_m",
                        "Altitude_geo_m", "Vitesse_kmh", "Cap_deg", "Au_sol",
                        "Pays", "Latitude", "Longitude", "Infraction"])
            for r in sorted(self.rows_cache, key=lambda x: x[2]):
                date, heure, ts, icao24, indicatif, alt_m, alt_geo, vitesse, cap, au_sol, pays, lat, lon, infraction = r
                w.writerow([date, heure, indicatif, icao24,
                             alt_m or "", alt_geo or "", vitesse or "", cap or "",
                             "oui" if au_sol else "non",
                             pays, lat, lon, infraction or ""])
        messagebox.showinfo("Export reussi", f"Fichier exporte :\n{path}")

    def _toggle_notif(self):
        self.notif_active = not self.notif_active
        if self.notif_active:
            self.btn_notif.config(text="Notifications : ON",
                                  bg="#1D9E75", activebackground="#0F6E56")
        else:
            self.btn_notif.config(text="Notifications : OFF",
                                  bg="#999999", activebackground="#777777")

    def _clear(self):
        if not messagebox.askyesno("Effacer", "Supprimer tous les passages ?"):
            return
        clear_db()
        self.seen_recently.clear()
        self.rows_cache = []
        self._apply_filters()
        self._update_stats()

    def _tick(self):
        if self.recording and self.next_scan_ts > 0:
            rem = max(0, int(self.next_scan_ts - time.time()))
            self.lbl_timer.config(text=f"Prochain scan dans {rem}s")
        self.after(1000, self._tick)

    def _set_status(self, txt, bg, fg):
        pass
