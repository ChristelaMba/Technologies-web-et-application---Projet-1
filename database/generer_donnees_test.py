
import sqlite3
from datetime import date, timedelta
from pathlib import Path

CHEMIN_BASE = Path(__file__).resolve().parent / "clinique.db"

NOMBRE_PATIENTS_CIBLE = 50
NOMBRE_RENDEZ_VOUS_CIBLE = 150

JOURS_SEMAINE = [
    "lundi",
    "mardi",
    "mercredi",
    "jeudi",
    "vendredi",
    "samedi",
    "dimanche",
]

CRENEAUX = [
    "08:00", "08:30",
    "09:00", "09:30",
    "10:00", "10:30",
    "11:00", "11:30",
]

NOMS = [
    "Manga", "Ngono", "Mbarga", "Essomba", "Tchoumi",
    "Nlend", "Fopa", "Biloa", "Moukoko", "Kamga",
    "Talla", "Mballa", "Nana", "Ekani", "Abena",
    "Ndongo", "Simo", "Mbah", "Kotto", "Onana",
]

PRENOMS = [
    "Marie", "Jean", "Paul", "Grâce", "Estelle",
    "Samuel", "Nadine", "Patrick", "Aline", "Christian",
    "Ruth", "David", "Sarah", "Daniel", "Joséphine",
    "Emmanuel", "Carine", "Alain", "Mireille", "Franck",
]

VILLES = [
    "Douala",
    "Yaoundé",
    "Bafoussam",
    "Garoua",
    "Kribi",
]

MOTIFS = [
    "Consultation générale",
    "Contrôle médical",
    "Douleurs persistantes",
    "Consultation de suivi",
    "Bilan de santé",
    "Consultation préventive",
]


def ajouter_patients(connexion):
    nombre_actuel = connexion.execute(
        "SELECT COUNT(*) FROM patients"
    ).fetchone()[0]

    numero = 1

    while nombre_actuel < NOMBRE_PATIENTS_CIBLE:
        nom = NOMS[(numero - 1) % len(NOMS)]
        prenom = PRENOMS[(numero - 1) % len(PRENOMS)]
        telephone = f"699{numero:06d}"
        naissance = date(1970, 1, 1) + timedelta(
            days=(numero * 137) % 15000
        )

        existe = connexion.execute(
            "SELECT 1 FROM patients WHERE telephone = ?",
            (telephone,),
        ).fetchone()

        if existe is None:
            connexion.execute(
                """
                INSERT INTO patients (
                    nom, prenom, telephone, date_naissance, ville
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    nom,
                    prenom,
                    telephone,
                    naissance.isoformat(),
                    VILLES[(numero - 1) % len(VILLES)],
                ),
            )
            nombre_actuel += 1

        numero += 1


def ajouter_rendez_vous(connexion):
    nombre_actuel = connexion.execute(
        "SELECT COUNT(*) FROM rendez_vous"
    ).fetchone()[0]

    if nombre_actuel >= NOMBRE_RENDEZ_VOUS_CIBLE:
        return

    medecins = connexion.execute(
        """
        SELECT id, jours_consultation
        FROM medecins
        ORDER BY id
        """
    ).fetchall()

    patients = connexion.execute(
        "SELECT id FROM patients ORDER BY id"
    ).fetchall()

    if not medecins or not patients:
        raise RuntimeError(
            "Il faut au moins un médecin et un patient."
        )

    patient_ids = [patient["id"] for patient in patients]
    aujourd_hui = date.today()

    # La période couvre octobre et novembre 2026.
    debut = date(2026, 10, 1)
    fin = date(2026, 11, 30)

    jour = debut
    index_patient = 0
    index_motif = 0

    while jour <= fin and nombre_actuel < NOMBRE_RENDEZ_VOUS_CIBLE:
        nom_jour = JOURS_SEMAINE[jour.weekday()]

        for medecin in medecins:
            jours_autorises = [
                element.strip().lower()
                for element in medecin["jours_consultation"].split(",")
            ]

            if nom_jour not in jours_autorises:
                continue

            for heure in CRENEAUX:
                if nombre_actuel >= NOMBRE_RENDEZ_VOUS_CIBLE:
                    break

                # Évite les créneaux déjà occupés par un rendez-vous
                # qui n'est pas annulé.
                occupe = connexion.execute(
                    """
                    SELECT 1
                    FROM rendez_vous
                    WHERE medecin_id = ?
                      AND date = ?
                      AND heure = ?
                      AND statut != 'annulé'
                    """,
                    (medecin["id"], jour.isoformat(), heure),
                ).fetchone()

                if occupe is not None:
                    continue

                # Ne crée pas de nouveaux rendez-vous dans le passé
                # avec un statut "prévu".
                if jour < aujourd_hui:
                    statut = "effectué"
                else:
                    statut = "prévu"

                patient_id = patient_ids[
                    index_patient % len(patient_ids)
                ]

                motif = MOTIFS[index_motif % len(MOTIFS)]

                try:
                    connexion.execute(
                        """
                        INSERT INTO rendez_vous (
                            patient_id, medecin_id, date, heure,
                            motif, statut
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            patient_id,
                            medecin["id"],
                            jour.isoformat(),
                            heure,
                            motif,
                            statut,
                        ),
                    )
                    nombre_actuel += 1
                    index_patient += 1
                    index_motif += 1

                except sqlite3.IntegrityError:
                    # Un créneau peut être déjà pris par une autre
                    # contrainte de la base.
                    continue

        jour += timedelta(days=1)

    if nombre_actuel < NOMBRE_RENDEZ_VOUS_CIBLE:
        raise RuntimeError(
            "Pas assez de créneaux disponibles pour atteindre "
            f"{NOMBRE_RENDEZ_VOUS_CIBLE} rendez-vous. "
            f"Nombre obtenu : {nombre_actuel}."
        )


def main():
    connexion = sqlite3.connect(CHEMIN_BASE)
    connexion.row_factory = sqlite3.Row
    connexion.execute("PRAGMA foreign_keys = ON")

    try:
        ajouter_patients(connexion)
        ajouter_rendez_vous(connexion)
        connexion.commit()

        print("Génération terminée.")
        print(
            "Patients :",
            connexion.execute(
                "SELECT COUNT(*) FROM patients"
            ).fetchone()[0],
        )
        print(
            "Rendez-vous :",
            connexion.execute(
                "SELECT COUNT(*) FROM rendez_vous"
            ).fetchone()[0],
        )

    except Exception:
        connexion.rollback()
        raise

    finally:
        connexion.close()


if __name__ == "__main__":
    main()
