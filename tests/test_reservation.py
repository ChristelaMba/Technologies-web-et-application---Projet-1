"""Tests du formulaire de réservation, sur une base temporaire."""
import shutil
import sqlite3
import tempfile
import threading
import unittest
from datetime import date, timedelta
from pathlib import Path

import app as application
from database import db as module_db

RACINE = Path(__file__).resolve().parent.parent
JOURS = application.JOURS_SEMAINE
CHAMPS = ["nom", "prenom", "telephone", "date_naissance",
          "ville", "date", "heure", "motif"]


def prochaine_date(jour, apres=1):
    """Prochaine date (après aujourd'hui) tombant sur le jour donné."""
    d = date.today() + timedelta(days=apres)
    while JOURS[d.weekday()] != jour:
        d += timedelta(days=1)
    return d


class BaseReservation(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.mkdtemp()
        self.chemin = Path(self.dossier) / "test.db"
        self.ancien_chemin = module_db.CHEMIN_BASE
        module_db.CHEMIN_BASE = self.chemin

        c = sqlite3.connect(self.chemin)
        c.executescript(
            (RACINE / "database" / "schema.sql").read_text(encoding="utf-8")
        )
        c.execute("ALTER TABLE patients ADD COLUMN date_creation TEXT")
        for id_, nom in [(1, "Dr Test"), (2, "Dr Autre")]:
            c.execute(
                "INSERT INTO medecins (id, nom, specialite, jours_consultation) "
                "VALUES (?, ?, 'Général', 'Lundi, Mercredi')",
                (id_, nom),
            )
        c.commit()
        c.close()

        application.app.config["TESTING"] = True
        self.client = application.app.test_client()
        self.lundi = prochaine_date("Lundi")

    def tearDown(self):
        module_db.CHEMIN_BASE = self.ancien_chemin
        shutil.rmtree(self.dossier, ignore_errors=True)

    def donnees(self, **surcharges):
        d = {
            "nom": "Mba",
            "prenom": "Awa",
            "telephone": "699123456",
            "date_naissance": "1990-05-12",
            "ville": "Douala",
            "date": self.lundi.isoformat(),
            "heure": "09:00",
            "motif": "Consultation de contrôle",
        }
        d.update(surcharges)
        # None = champ absent de la requête
        return {k: v for k, v in d.items() if v is not None}

    def poster(self, medecin_id=1, **surcharges):
        return self.client.post(
            f"/reservation/{medecin_id}", data=self.donnees(**surcharges)
        )

    def compter(self, table):
        c = sqlite3.connect(self.chemin)
        n = c.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        c.close()
        return n

    def vider(self):
        c = sqlite3.connect(self.chemin)
        c.execute("DELETE FROM rendez_vous")
        c.execute("DELETE FROM patients")
        c.commit()
        c.close()

    def assert_refus(self, reponse, extrait=None):
        self.assertEqual(reponse.status_code, 200)
        page = reponse.get_data(as_text=True)
        self.assertIn("booking-message-error", page)
        self.assertNotIn("booking-message-success", page)
        if extrait:
            self.assertIn(extrait, page)
        self.assertEqual(self.compter("rendez_vous"), 0)
        self.assertEqual(self.compter("patients"), 0)

    def assert_succes(self, reponse):
        self.assertIn("booking-message-success", reponse.get_data(as_text=True))


class TestChampsObligatoires(BaseReservation):
    def test_champ_absent(self):
        for champ in CHAMPS:
            with self.subTest(champ=champ):
                self.assert_refus(self.poster(**{champ: None}))

    def test_champ_vide_ou_espaces(self):
        for champ in CHAMPS:
            for valeur in ["", "   "]:
                with self.subTest(champ=champ, valeur=valeur):
                    self.assert_refus(self.poster(**{champ: valeur}))

    def test_message_explicatif(self):
        self.assert_refus(self.poster(nom=""), "remplir tous les champs")

    def test_medecin_inconnu(self):
        self.assertEqual(self.poster(medecin_id=999).status_code, 404)
        self.assertEqual(self.compter("rendez_vous"), 0)

    def test_champs_html_required(self):
        page = self.client.get("/reservation/1").get_data(as_text=True)
        self.assertGreaterEqual(page.count("required"), len(CHAMPS))


class TestDates(BaseReservation):
    def test_date_passee(self):
        hier = (date.today() - timedelta(days=1)).isoformat()
        self.assert_refus(self.poster(date=hier), "ultérieure")

    def test_date_du_jour_refusee(self):
        self.assert_refus(
            self.poster(date=date.today().isoformat()), "ultérieure"
        )

    def test_date_mal_formatee(self):
        for valeur in ["31/12/2030", "2030-13-45", "abc", "2030-02-30",
                       "20301230", "2030-W01-1", "2030-12-30T10:00"]:
            with self.subTest(valeur=valeur):
                self.assert_refus(self.poster(date=valeur))

    def test_jour_non_autorise(self):
        mardi = prochaine_date("Mardi")
        self.assert_refus(
            self.poster(date=mardi.isoformat()), "ne consulte pas"
        )

    def test_heure_hors_horaires(self):
        for h in ["07:00", "12:00", "9:00", "abc"]:
            with self.subTest(heure=h):
                self.assert_refus(self.poster(heure=h))

    def test_naissance_future(self):
        futur = (date.today() + timedelta(days=5)).isoformat()
        self.assert_refus(self.poster(date_naissance=futur))

    def test_naissance_mal_formatee(self):
        for valeur in ["12/05/1990", "19900512x", "1990-02-30", "19900512"]:
            with self.subTest(valeur=valeur):
                self.assert_refus(self.poster(date_naissance=valeur))


class TestTelephone(BaseReservation):
    def test_formats_valides(self):
        for tel in ["699123456", "+237699123456", "237699123456",
                    " 699 12 34 56 ", "6-99.12.34.56"]:
            with self.subTest(tel=tel):
                self.vider()
                self.assert_succes(self.poster(telephone=tel))
                c = sqlite3.connect(self.chemin)
                enregistre = c.execute(
                    "SELECT telephone FROM patients"
                ).fetchone()[0]
                c.close()
                self.assertEqual(enregistre, "+237699123456")

    def test_formats_invalides(self):
        for tel in ["69912345", "6991234567", "+2376991234567", "69912345a",
                    "abcdefghi", "199123456", "+33612345678", "", "     "]:
            with self.subTest(tel=tel):
                self.assert_refus(self.poster(telephone=tel))

    def test_patient_existant_reutilise(self):
        self.poster()
        self.poster(heure="09:30", nom="Autre")
        self.assertEqual(self.compter("patients"), 1)
        self.assertEqual(self.compter("rendez_vous"), 2)


class TestDoubleReservation(BaseReservation):
    def test_reservation_valide(self):
        self.assert_succes(self.poster())
        self.assertEqual(self.compter("rendez_vous"), 1)
        c = sqlite3.connect(self.chemin)
        enregistree = c.execute("SELECT date FROM rendez_vous").fetchone()[0]
        c.close()
        self.assertEqual(enregistree, self.lundi.isoformat())

    def test_creneau_deja_pris(self):
        self.poster()
        r = self.poster(telephone="677000111", nom="Autre")
        self.assertIn("booking-message-error", r.get_data(as_text=True))
        self.assertEqual(self.compter("rendez_vous"), 1)
        # le patient n'est pas créé si la réservation échoue
        self.assertEqual(self.compter("patients"), 1)

    def test_meme_creneau_autre_medecin(self):
        self.poster(medecin_id=1)
        self.assert_succes(self.poster(medecin_id=2, telephone="677000111"))
        self.assertEqual(self.compter("rendez_vous"), 2)

    def test_creneau_occupe_absent_de_l_api(self):
        self.poster()
        r = self.client.get(
            f"/api/creneaux?medecin_id=1&date={self.lundi.isoformat()}"
        )
        self.assertNotIn("09:00", r.get_json()["creneaux"])

    def test_creneau_annule_reutilisable(self):
        self.poster()
        c = sqlite3.connect(self.chemin)
        c.execute("UPDATE rendez_vous SET statut = 'annulé'")
        c.commit()
        c.close()
        self.assert_succes(self.poster(telephone="677000111", nom="Autre"))
        self.assertEqual(self.compter("rendez_vous"), 2)

    def test_reservations_concurrentes(self):
        resultats = []
        barriere = threading.Barrier(6)

        def tenter(i):
            client = application.app.test_client()
            barriere.wait()
            r = client.post("/reservation/1", data=self.donnees(
                telephone=f"69900000{i}", nom=f"P{i}"))
            resultats.append(
                "booking-message-success" in r.get_data(as_text=True)
            )

        fils = [threading.Thread(target=tenter, args=(i,)) for i in range(6)]
        for f in fils:
            f.start()
        for f in fils:
            f.join()
        self.assertEqual(sum(resultats), 1)
        self.assertEqual(self.compter("rendez_vous"), 1)
        self.assertEqual(self.compter("patients"), 1)


if __name__ == "__main__":
    unittest.main()
