
import sqlite3
from pathlib import Path

FICHIER_DB = Path(__file__).resolve().parent / "clinique.db"

connexion = sqlite3.connect(FICHIER_DB)
connexion.row_factory = sqlite3.Row

try:
    rendez_vous = connexion.execute(
        """
        SELECT
            rv.id,
            rv.date,
            rv.heure,
            rv.statut,
            p.nom,
            p.prenom,
            m.nom AS nom_medecin,
            m.specialite
        FROM rendez_vous AS rv
        JOIN patients AS p ON p.id = rv.patient_id
        JOIN medecins AS m ON m.id = rv.medecin_id
        WHERE rv.statut = 'effectué'
          AND rv.date > date('now', 'localtime')
        ORDER BY rv.date, rv.heure
        """
    ).fetchall()

    if not rendez_vous:
        print("Aucune anomalie trouvée.")

    for rv in rendez_vous:
        print(
            f"ID : {rv['id']} | "
            f"Date : {rv['date']} | "
            f"Heure : {rv['heure']} | "
            f"Patient : {rv['prenom']} {rv['nom']} | "
            f"Médecin : {rv['nom_medecin']} | "
            f"Spécialité : {rv['specialite']} | "
            f"Statut : {rv['statut']}"
        )

finally:
    connexion.close()
