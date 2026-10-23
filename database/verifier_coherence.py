
import sqlite3
from datetime import date
from pathlib import Path

FICHIER_DB = Path(__file__).resolve().parent / "clinique.db"
AUJOURD_HUI = date.today().isoformat()

connexion = sqlite3.connect(FICHIER_DB)

try:
    controles = [
        (
            "Rendez-vous prévus dans le passé",
            """
            SELECT COUNT(*)
            FROM rendez_vous
            WHERE statut = 'prévu' AND date < ?
            """,
        ),
        (
            "Rendez-vous effectués dans le futur",
            """
            SELECT COUNT(*)
            FROM rendez_vous
            WHERE statut = 'effectué' AND date > ?
            """,
        ),
        (
            "Rendez-vous prévus aujourd'hui",
            """
            SELECT COUNT(*)
            FROM rendez_vous
            WHERE statut = 'prévu' AND date = ?
            """,
        ),
    ]

    print(f"Date de référence : {AUJOURD_HUI}\n")

    for description, requete in controles:
        resultat = connexion.execute(
            requete, (AUJOURD_HUI,)
        ).fetchone()[0]

        print(f"{description} : {resultat}")

finally:
    connexion.close()
