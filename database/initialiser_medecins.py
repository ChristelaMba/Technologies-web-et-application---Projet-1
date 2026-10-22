
import sqlite3
from pathlib import Path


CHEMIN_BASE = Path(__file__).resolve().parent / "clinique.db"

medecins = [
    ("Dr Alain Mbarga", "Médecine générale", None, "Lundi, Mercredi, Vendredi"),
    ("Dr Mireille Ngono", "Médecine générale", None, "Mardi, Jeudi"),
    ("Dr Samuel Tchoumi", "Pédiatrie", None, "Lundi, Mardi, Jeudi"),
    ("Dr Nadège Essomba", "Pédiatrie", None, "Mercredi, Vendredi"),
    ("Dr Patrick Moukoko", "Gynécologie", None, "Lundi, Mercredi, Samedi"),
    ("Dr Grâce Nlend", "Gynécologie", None, "Mardi, Jeudi, Vendredi"),
    ("Dr Christian Fopa", "Cardiologie", None, "Mardi, Mercredi, Samedi"),
    ("Dr Estelle Biloa", "Cardiologie", None, "Lundi, Jeudi, Vendredi"),
]

connexion = sqlite3.connect(CHEMIN_BASE)

try:
    connexion.executemany("""
        INSERT INTO medecins (nom, specialite, photo, jours_consultation)
        SELECT ?, ?, ?, ?
        WHERE NOT EXISTS (
            SELECT 1
            FROM medecins
            WHERE nom = ?
        )
    """, [(*medecin, medecin[0]) for medecin in medecins])

    connexion.commit()
    print("Initialisation terminée.")
    print(
        "Nombre de médecins enregistrés :",
        connexion.execute("SELECT COUNT(*) FROM medecins").fetchone()[0]
    )
except sqlite3.Error as erreur:
    connexion.rollback()
    print("Erreur pendant l'initialisation :", erreur)
finally:
    connexion.close()
