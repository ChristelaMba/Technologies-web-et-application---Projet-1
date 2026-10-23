
import shutil
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
FICHIER_DB = DOSSIER / "clinique.db"

# Les rendez-vous 1 à 5 sont conservés.
PREMIER_ID_TEST = 6

DATE_DEBUT = date(2026, 10, 1)
DATE_FIN = date(2026, 11, 30)

CRENEAUX = [
    "08:00",
    "08:30",
    "09:00",
    "09:30",
    "10:00",
    "10:30",
    "11:00",
    "11:30",
]

JOURS = [
    "lundi",
    "mardi",
    "mercredi",
    "jeudi",
    "vendredi",
    "samedi",
    "dimanche",
]


def jours_du_medecin(texte):
    return {
        jour.strip().lower()
        for jour in texte.split(",")
        if jour.strip()
    }


def dates_entre(debut, fin):
    jour = debut

    while jour <= fin:
        yield jour
        jour += timedelta(days=1)


def trouver_creneau(medecin_id, debut, fin, jours_consultation, occupes):
    for jour in dates_entre(debut, fin):
        nom_jour = JOURS[jour.weekday()]

        if nom_jour not in jours_consultation[medecin_id]:
            continue

        for heure in CRENEAUX:
            creneau = (medecin_id, jour.isoformat(), heure)

            if creneau not in occupes:
                occupes.add(creneau)
                return jour.isoformat(), heure

    raise RuntimeError(
        f"Aucun créneau disponible pour le médecin {medecin_id} "
        f"entre le {debut} et le {fin}."
    )


def main():
    if not FICHIER_DB.exists():
        raise FileNotFoundError(
            f"Base de données introuvable : {FICHIER_DB}"
        )

    # Crée une copie de sécurité avant toute modification.
    horodatage = datetime.now().strftime("%Y%m%d_%H%M%S")
    sauvegarde = DOSSIER / f"clinique_avant_repartition_{horodatage}.db"
    shutil.copy2(FICHIER_DB, sauvegarde)

    connexion = sqlite3.connect(FICHIER_DB)
    connexion.row_factory = sqlite3.Row

    try:
        connexion.execute("PRAGMA foreign_keys = ON")

        with connexion:
            medecins = connexion.execute(
                """
                SELECT id, jours_consultation
                FROM medecins
                """
            ).fetchall()

            jours_consultation = {
                medecin["id"]: jours_du_medecin(
                    medecin["jours_consultation"] or ""
                )
                for medecin in medecins
            }

            rendez_vous = connexion.execute(
                """
                SELECT id, medecin_id, date, heure, statut
                FROM rendez_vous
                ORDER BY id
                """
            ).fetchall()

            if len(rendez_vous) != 150:
                raise RuntimeError(
                    f"Le script attend 150 rendez-vous, "
                    f"mais en trouve {len(rendez_vous)}. "
                    "Aucune modification n'a été validée."
                )

            initiaux = [
                rv for rv in rendez_vous
                if rv["id"] < PREMIER_ID_TEST
            ]

            tests = [
                rv for rv in rendez_vous
                if rv["id"] >= PREMIER_ID_TEST
            ]

            if len(initiaux) != 5 or len(tests) != 145:
                raise RuntimeError(
                    "Les identifiants ne correspondent pas "
                    "à la répartition attendue : 5 rendez-vous "
                    "initiaux et 145 rendez-vous de test."
                )

            occupes = {
                (rv["medecin_id"], rv["date"], rv["heure"])
                for rv in initiaux
            }

            # Vérifie que tous les médecins utilisés existent.
            for rv in tests:
                if rv["medecin_id"] not in jours_consultation:
                    raise RuntimeError(
                        f"Médecin introuvable pour le rendez-vous {rv['id']}."
                    )

            aujourd_hui = date.today()
            debut_passe = DATE_DEBUT
            fin_passe = min(DATE_FIN, aujourd_hui - timedelta(days=1))
            debut_futur = max(DATE_DEBUT, aujourd_hui + timedelta(days=1))
            fin_futur = DATE_FIN

            if debut_passe > fin_passe or debut_futur > fin_futur:
                raise RuntimeError(
                    "La période de test ne contient pas assez "
                    "de dates passées ou futures."
                )

            # Prépare les statuts des 145 rendez-vous générés.
            repartition = (
                [("effectué", debut_passe, fin_passe)] * 39
                + [("annulé", DATE_DEBUT, DATE_FIN)] * 19
                + [("prévu", debut_futur, fin_futur)] * 87
            )

            # Libère les anciens créneaux des rendez-vous de test.
            # Chaque date temporaire est différente pour éviter
            # les conflits avec la contrainte d'unicité.
            for rv in tests:
                date_temporaire = (
                    date(2099, 1, 1) + timedelta(days=rv["id"])
                ).isoformat()

                connexion.execute(
                    """
                    UPDATE rendez_vous
                    SET date = ?, heure = ?
                    WHERE id = ?
                    """,
                    (date_temporaire, "00:00", rv["id"]),
                )

            # Replace les rendez-vous selon leur statut et
            # les jours de consultation de chaque médecin.
            for rv, (statut, debut, fin) in zip(tests, repartition):
                nouvelle_date, nouvelle_heure = trouver_creneau(
                    rv["medecin_id"],
                    debut,
                    fin,
                    jours_consultation,
                    occupes,
                )

                connexion.execute(
                    """
                    UPDATE rendez_vous
                    SET date = ?, heure = ?, statut = ?
                    WHERE id = ?
                    """,
                    (
                        nouvelle_date,
                        nouvelle_heure,
                        statut,
                        rv["id"],
                    ),
                )

        print("Réorganisation terminée.")
        print(f"Sauvegarde créée : {sauvegarde.name}")

        resultat = connexion.execute(
            """
            SELECT statut, COUNT(*) AS nombre
            FROM rendez_vous
            GROUP BY statut
            ORDER BY statut
            """
        ).fetchall()

        print("\nRépartition finale :")
        for ligne in resultat:
            print(f"- {ligne['statut']} : {ligne['nombre']}")

        total = connexion.execute(
            "SELECT COUNT(*) FROM rendez_vous"
        ).fetchone()[0]

        print(f"- Total : {total}")

        doublons = connexion.execute(
            """
            SELECT medecin_id, date, heure, COUNT(*) AS nombre
            FROM rendez_vous
            GROUP BY medecin_id, date, heure
            HAVING COUNT(*) > 1
            """
        ).fetchall()

        print(f"- Doublons de créneaux : {len(doublons)}")

    except Exception:
        connexion.rollback()
        print(
            "\nUne erreur est survenue. "
            "Les modifications de cette opération ont été annulées."
        )
        raise

    finally:
        connexion.close()


if __name__ == "__main__":
    main()
