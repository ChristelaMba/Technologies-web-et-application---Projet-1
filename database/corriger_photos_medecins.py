
import sqlite3
from pathlib import Path

CHEMIN_BASE = Path(__file__).resolve().parent / "clinique.db"

photos = [
    ("medecin-1.jpg", "Dr Alain Mbarga"),
    ("medecin-3.jpg", "Dr Mireille Ngono"),
    ("medecin-2.jpg", "Dr Samuel Tchoumi"),
    ("medecin-4.jpg", "Dr Nadège Essomba"),
    ("medecin-8.jpg", "Dr Patrick Moukoko"),
    ("medecin-6.jpg", "Dr Grâce Nlend"),
    ("medecin-7.jpg", "Dr Christian Fopa"),
    ("medecin-5.jpg", "Dr Estelle Biloa"),
]

connexion = sqlite3.connect(CHEMIN_BASE)

try:
    for photo, nom in photos:
        connexion.execute(
            "UPDATE medecins SET photo = ? WHERE nom = ?",
            (photo, nom),
        )

    connexion.commit()

    medecins = connexion.execute(
        "SELECT nom, photo FROM medecins ORDER BY id"
    ).fetchall()

    print("Associations des photos mises à jour :")
    for nom, photo in medecins:
        print(f"{nom} : {photo}")

except sqlite3.Error as erreur:
    connexion.rollback()
    print("Erreur pendant la mise à jour :", erreur)

finally:
    connexion.close()
