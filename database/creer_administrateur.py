
import getpass
import sqlite3
from pathlib import Path
from werkzeug.security import generate_password_hash

CHEMIN_BASE = Path(__file__).resolve().parent / "clinique.db"


def creer_administrateur():
    identifiant = input("Identifiant administrateur : ").strip()

    if not identifiant:
        print("L'identifiant est obligatoire.")
        return

    mot_de_passe = getpass.getpass("Mot de passe : ")
    confirmation = getpass.getpass("Confirmer le mot de passe : ")

    if len(mot_de_passe) < 8:
        print("Le mot de passe doit contenir au moins 8 caractères.")
        return

    if mot_de_passe != confirmation:
        print("Les mots de passe ne correspondent pas.")
        return

    connexion = sqlite3.connect(CHEMIN_BASE)

    try:
        connexion.execute(
            """
            INSERT INTO administrateurs (identifiant, mot_de_passe_hash)
            VALUES (?, ?)
            """,
            (identifiant, generate_password_hash(mot_de_passe)),
        )
        connexion.commit()
        print("Compte administrateur créé avec succès.")

    except sqlite3.IntegrityError:
        print("Cet identifiant existe déjà.")

    finally:
        connexion.close()


if __name__ == "__main__":
    creer_administrateur()
