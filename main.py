"""
Radar de Survol Aerien
Application Windows de David Coldefy avec Claude
Version 1.9 - PDF A4, choix destinataire, filtrage avions de ligne,
              majuscules nom/prenom, tri initial altitude croissante,
              commune configurable via le profil utilisateur

Point d'entrée de l'application.
"""

from app import RadarApp

if __name__ == "__main__":
    app = RadarApp()
    app.mainloop()
