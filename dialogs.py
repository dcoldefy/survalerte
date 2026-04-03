"""
Dialogues Tkinter — choix du destinataire, saisie du profil, menu contextuel.
"""

import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from config import DESTINATAIRES
from api import chercher_communes
from database import save_profil
from pdf import generer_plainte_pdf
from utils import majuscules


# ---- Dialogue choix destinataire --------------------------------------------

class DialogueDestinataire(tk.Toplevel):

    def __init__(self, parent, profil):
        super().__init__(parent)
        self.title("Choisir le destinataire de la plainte")
        self.resizable(False, False)
        self.grab_set()
        self.focus_force()
        self.result = None
        self.configure(bg="#F8F8F6")
        self.update_idletasks()
        w, h = 500, 340
        x = parent.winfo_x() + (parent.winfo_width()  - w) // 2
        y = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self._build(profil)

    def _build(self, profil):
        hdr = tk.Frame(self, bg="#A32D2D", pady=12, padx=20)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Choisir le destinataire de la plainte",
                 font=("Segoe UI", 12, "bold"), bg="#A32D2D", fg="#FFFFFF").pack(anchor="w")
        tk.Label(hdr, text="Selectionnez l'organisme auquel adresser votre plainte.",
                 font=("Segoe UI", 8), bg="#A32D2D", fg="#F7C1C1").pack(anchor="w")

        form = tk.Frame(self, bg="#F8F8F6", padx=20, pady=12)
        form.pack(fill="both", expand=True)

        tk.Label(form, text="Destinataire :", font=("Segoe UI", 9, "bold"),
                 bg="#F8F8F6", fg="#444").pack(anchor="w", pady=(0, 6))

        self.choix = tk.IntVar(value=0)

        options = []
        for i, d in enumerate(DESTINATAIRES):
            if d["nom"] is None and profil:
                cp    = profil.get("code_postal", "")
                ville = profil.get("ville", "")
                label = f"Mairie de {ville}"
                desc  = f"Mairie de {ville} - {cp} {ville}"
            else:
                label = d["label"]
                desc  = f"{d['nom']} - {d['adresse']}, {d['cp_ville']}"
            options.append((i, label, desc))

        for i, label, desc in options:
            fr = tk.Frame(form, bg="#F8F8F6")
            fr.pack(fill="x", pady=3)
            rb = tk.Radiobutton(fr, text=label, variable=self.choix, value=i,
                                font=("Segoe UI", 9, "bold"),
                                bg="#F8F8F6", fg="#1a1a1a",
                                activebackground="#F8F8F6",
                                cursor="hand2")
            rb.pack(anchor="w")
            tk.Label(fr, text=desc, font=("Segoe UI", 8),
                     bg="#F8F8F6", fg="#888").pack(anchor="w", padx=(22, 0))

        self.lbl_apercu = tk.Label(form, text="",
                                    font=("Segoe UI", 8, "italic"),
                                    bg="#E6F1FB", fg="#185FA5",
                                    wraplength=440, justify="left",
                                    padx=8, pady=4)
        self.lbl_apercu.pack(fill="x", pady=(10, 0))
        self.choix.trace_add("write", lambda *a: self._maj_apercu(profil))
        self._maj_apercu(profil)

        bf = tk.Frame(self, bg="#F8F8F6", padx=20, pady=10)
        bf.pack(fill="x", side="bottom")
        tk.Button(bf, text="Valider et generer le PDF",
                  command=self._valider,
                  font=("Segoe UI", 10, "bold"),
                  bg="#A32D2D", fg="white",
                  activebackground="#791F1F",
                  relief="flat", padx=20, pady=6,
                  cursor="hand2").pack(side="right")
        tk.Button(bf, text="Annuler", command=self.destroy,
                  font=("Segoe UI", 9), bg="#E8E8E6", fg="#333",
                  relief="flat", padx=14, pady=6,
                  cursor="hand2").pack(side="right", padx=(0, 8))
        self.bind("<Return>", lambda e: self._valider())

    def _maj_apercu(self, profil):
        idx  = self.choix.get()
        dest = DESTINATAIRES[idx]
        if dest["nom"] is None and profil:
            ville = profil.get("ville", "")
            cp    = profil.get("code_postal", "")
            nom_d = f"Mairie de {ville}"
            adr_d = f"{cp} {ville}".strip()
        else:
            nom_d = dest.get("nom", "")
            adr_d = f"{dest.get('adresse', '')} - {dest.get('cp_ville', '')}".strip(" -")
        self.lbl_apercu.config(text=f"Destinataire : {nom_d}  |  {adr_d}")

    def _valider(self):
        self.result = self.choix.get()
        self.destroy()


# ---- Dialogue profil --------------------------------------------------------

class DialogueProfil(tk.Toplevel):

    def __init__(self, parent, profil=None, titre="Bienvenue"):
        super().__init__(parent)
        self.title(titre)
        self.resizable(False, False)
        self.grab_set()
        self.focus_force()
        self.result = None
        self.configure(bg="#F8F8F6")
        self.update_idletasks()
        w, h = 460, 450
        x = parent.winfo_x() + (parent.winfo_width()  - w) // 2
        y = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self._build(profil)

    def _build(self, p):
        hdr = tk.Frame(self, bg="#185FA5", pady=14, padx=20)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Informations utilisateur",
                 font=("Segoe UI", 13, "bold"), bg="#185FA5", fg="#FFFFFF").pack(anchor="w")
        tk.Label(hdr, text="Ces informations sont stockees localement sur votre PC.",
                 font=("Segoe UI", 8), bg="#185FA5", fg="#B5D4F4").pack(anchor="w")

        form = tk.Frame(self, bg="#F8F8F6", padx=24, pady=8)
        form.pack(fill="both", expand=True)
        self.champs = {}

        for key, label in [("prenom", "Prenom *"), ("nom", "Nom *"), ("adresse", "Adresse")]:
            tk.Label(form, text=label, font=("Segoe UI", 9),
                     bg="#F8F8F6", fg="#444").pack(anchor="w", pady=(6, 1))
            e = tk.Entry(form, font=("Segoe UI", 10), relief="flat",
                         bg="#FFFFFF", fg="#1a1a1a",
                         highlightthickness=1,
                         highlightbackground="#CCCCCC",
                         highlightcolor="#185FA5")
            e.pack(fill="x", ipady=4)
            val = p.get(key, "") if p else ""
            if key in ("nom", "prenom") and val:
                val = val.upper()
            if val:
                e.insert(0, val)
            if key in ("nom", "prenom"):
                e.bind("<KeyRelease>", lambda ev, ent=e: self._maj_auto(ent))
            self.champs[key] = e

        tk.Label(form, text="Code postal *", font=("Segoe UI", 9),
                 bg="#F8F8F6", fg="#444").pack(anchor="w", pady=(6, 1))
        cp_frame = tk.Frame(form, bg="#F8F8F6")
        cp_frame.pack(fill="x")
        self.champs["code_postal"] = tk.Entry(cp_frame, font=("Segoe UI", 10),
                         relief="flat", bg="#FFFFFF", fg="#1a1a1a",
                         highlightthickness=1,
                         highlightbackground="#CCCCCC",
                         highlightcolor="#185FA5", width=10)
        self.champs["code_postal"].pack(side="left", ipady=4)
        if p and p.get("code_postal"):
            self.champs["code_postal"].insert(0, p["code_postal"])

        self.btn_rech = tk.Button(cp_frame, text="Rechercher les communes",
                  command=self._rechercher,
                  font=("Segoe UI", 9), bg="#185FA5", fg="white",
                  activebackground="#0C447C", relief="flat",
                  padx=10, pady=3, cursor="hand2")
        self.btn_rech.pack(side="left", padx=(8, 0))
        self.lbl_rech = tk.Label(cp_frame, text="", font=("Segoe UI", 8),
                                  bg="#F8F8F6", fg="#888")
        self.lbl_rech.pack(side="left", padx=(8, 0))

        tk.Label(form, text="Commune *", font=("Segoe UI", 9),
                 bg="#F8F8F6", fg="#444").pack(anchor="w", pady=(6, 1))
        self.combo_ville = ttk.Combobox(form, font=("Segoe UI", 10),
                                         state="readonly", width=35)
        self.combo_ville.pack(fill="x", ipady=3)
        if p and p.get("ville"):
            self.combo_ville["values"] = [p["ville"]]
            self.combo_ville.set(p["ville"])
            if p.get("code_postal"):
                threading.Thread(target=self._init_communes,
                                 args=(p["code_postal"], p["ville"]),
                                 daemon=True).start()

        tk.Label(form, text="* champs obligatoires - Entrez le code postal puis cliquez Rechercher",
                 font=("Segoe UI", 7), bg="#F8F8F6", fg="#aaa").pack(anchor="w", pady=(4, 0))

        bf = tk.Frame(self, bg="#F8F8F6", padx=24, pady=10)
        bf.pack(fill="x", side="bottom")
        tk.Button(bf, text="Valider", command=self._valider,
                  font=("Segoe UI", 10, "bold"), bg="#1D9E75", fg="white",
                  activebackground="#0F6E56", relief="flat",
                  padx=20, pady=6, cursor="hand2").pack(side="right")
        if p:
            tk.Button(bf, text="Annuler", command=self.destroy,
                      font=("Segoe UI", 9), bg="#E8E8E6", fg="#333",
                      relief="flat", padx=14, pady=6,
                      cursor="hand2").pack(side="right", padx=(0, 8))

        self.bind("<Return>", lambda e: self._valider())
        self.champs["code_postal"].bind("<Return>", lambda e: self._rechercher())
        self.champs["prenom"].focus_set()

    def _maj_auto(self, entry):
        pos = entry.index(tk.INSERT)
        val = entry.get().upper()
        entry.delete(0, tk.END)
        entry.insert(0, val)
        try:
            entry.icursor(pos)
        except Exception:
            pass

    def _init_communes(self, cp, selection):
        communes = chercher_communes(cp)
        if communes:
            self.after(0, lambda: self._maj_communes(communes, selection))

    def _rechercher(self):
        cp = self.champs["code_postal"].get().strip()
        if len(cp) != 5 or not cp.isdigit():
            messagebox.showwarning("Code postal invalide",
                "Le code postal doit contenir exactement 5 chiffres.", parent=self)
            return
        self.lbl_rech.config(text="Recherche...")
        self.btn_rech.config(state="disabled")
        def fetch():
            communes = chercher_communes(cp)
            self.after(0, lambda: self._maj_communes(communes, None))
        threading.Thread(target=fetch, daemon=True).start()

    def _maj_communes(self, communes, selection):
        self.btn_rech.config(state="normal")
        if not communes:
            self.lbl_rech.config(text="Aucune commune trouvee")
            self.combo_ville["values"] = []
            self.combo_ville.set("")
            return
        self.combo_ville["values"] = communes
        if selection and selection in communes:
            self.combo_ville.set(selection)
        else:
            self.combo_ville.current(0)
        n = len(communes)
        self.lbl_rech.config(text=f"{n} commune{'s' if n > 1 else ''} trouvee{'s' if n > 1 else ''}")

    def _valider(self):
        prenom  = majuscules(self.champs["prenom"].get())
        nom     = majuscules(self.champs["nom"].get())
        adresse = self.champs["adresse"].get().strip()
        cp      = self.champs["code_postal"].get().strip()
        ville   = self.combo_ville.get().strip()
        if not prenom or not nom:
            messagebox.showwarning("Champs manquants",
                "Merci de renseigner le prenom et le nom.", parent=self)
            return
        if not cp or not ville:
            messagebox.showwarning("Champs manquants",
                "Merci de renseigner le code postal et de selectionner une commune.", parent=self)
            return
        self.result = {"prenom": prenom, "nom": nom, "adresse": adresse,
                       "code_postal": cp, "ville": ville}
        save_profil(nom, prenom, adresse, cp, ville)
        self.destroy()


# ---- Menu contextuel --------------------------------------------------------

class MenuContextuel(tk.Menu):

    def __init__(self, parent, vol, profil):
        super().__init__(parent, tearoff=0, font=("Segoe UI", 9))
        self.parent  = parent
        self.vol     = vol
        self.profil  = profil

        indicatif = vol.get("indicatif", "")
        icao24    = vol.get("icao24", "")
        ref = indicatif if indicatif and indicatif != "-" else icao24

        self.add_command(
            label=f"Suivre {ref} sur Flightradar24",
            command=self._ouvrir_flightradar)
        self.add_separator()
        self.add_command(
            label="Generer une plainte PDF pour ce vol",
            command=self._choisir_destinataire,
            foreground="#A32D2D")

    def _ouvrir_flightradar(self):
        import webbrowser
        indicatif = (self.vol.get("indicatif", "") or "").strip()
        icao24    = (self.vol.get("icao24", "") or "").strip().lower()
        if indicatif and indicatif != "-":
            url = f"https://www.flightradar24.com/{indicatif}"
        elif icao24:
            url = f"https://www.flightradar24.com/data/aircraft/{icao24}"
        else:
            url = "https://www.flightradar24.com/"
        webbrowser.open(url)

    def _choisir_destinataire(self):
        if not self.profil:
            messagebox.showwarning("Profil manquant",
                "Veuillez d'abord renseigner votre profil.")
            return
        dlg = DialogueDestinataire(self.parent, self.profil)
        self.parent.wait_window(dlg)
        if dlg.result is None:
            return
        idx  = dlg.result
        dest = dict(DESTINATAIRES[idx])

        if dest["nom"] is None:
            ville = self.profil.get("ville", "")
            cp    = self.profil.get("code_postal", "")
            dest["nom"]      = f"Monsieur le Maire de {ville}"
            dest["adresse"]  = f"Mairie de {ville}"
            dest["cp_ville"] = f"{cp} {ville}".strip()

        try:
            chemin = generer_plainte_pdf(self.profil, self.vol, dest)
            os.startfile(chemin)
            messagebox.showinfo("Plainte generee",
                f"Document PDF cree sur votre Bureau :\n\n{chemin}\n\n"
                f"Il s'ouvre automatiquement. Imprimez-le et signez-le.")
        except RuntimeError as e:
            messagebox.showerror("Module manquant", str(e))
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible de generer la plainte :\n{e}")
