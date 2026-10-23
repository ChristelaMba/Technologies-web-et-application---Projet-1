import os
import secrets
import sqlite3
from datetime import date
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    abort,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
    flash,
)

from werkzeug.security import check_password_hash

from database.db import get_db
import re
import sqlite3
from datetime import date

from flask import (
    Flask,
    abort,
    g,
    jsonify,
    render_template,
    request,
)

from database.db import get_db


app = Flask(__name__)

# Conserve la clé de session entre les redémarrages.
DOSSIER_INSTANCE = Path(app.root_path) / "instance"
DOSSIER_INSTANCE.mkdir(exist_ok=True)

FICHIER_CLE = DOSSIER_INSTANCE / "secret_key.txt"

if not FICHIER_CLE.exists():
    FICHIER_CLE.write_text(secrets.token_hex(32), encoding="utf-8")

app.config["SECRET_KEY"] = (
    os.environ.get("FLASK_SECRET_KEY")
    or FICHIER_CLE.read_text(encoding="utf-8").strip()
)

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

JOURS_SEMAINE = [
    "Lundi",
    "Mardi",
    "Mercredi",
    "Jeudi",
    "Vendredi",
    "Samedi",
    "Dimanche",
]

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


def medecin_existe(medecin_id):
    connexion = get_db()

    return connexion.execute(
        "SELECT * FROM medecins WHERE id = ?",
        (medecin_id,),
    ).fetchone()


def jour_consultation(medecin, date_consultation):
    jour = JOURS_SEMAINE[date_consultation.weekday()]

    jours = [
        element.strip().lower()
        for element in medecin["jours_consultation"].split(",")
    ]

    return jour.lower() in jours


def telephone_valide(telephone):
    telephone = telephone.strip().replace(" ", "")
    telephone = telephone.replace("-", "").replace(".", "")

    if not re.fullmatch(r"(?:\+?237)?[2368]\d{8}", telephone):
        return None

    if telephone.startswith("+237"):
        return telephone

    if telephone.startswith("237"):
        return "+" + telephone

    return "+237" + telephone


def creneaux_disponibles(medecin_id, date_consultation):
    connexion = get_db()
    medecin = medecin_existe(medecin_id)

    if medecin is None:
        return []

    try:
        date_choisie = date.fromisoformat(date_consultation)
    except (ValueError, TypeError):
        return []

    if date_choisie <= date.today():
        return []

    if not jour_consultation(medecin, date_choisie):
        return []

    rendez_vous = connexion.execute(
        """
        SELECT heure
        FROM rendez_vous
        WHERE medecin_id = ?
          AND date = ?
          AND statut != 'annulé'
        """,
        (medecin_id, date_consultation),
    ).fetchall()

    heures_occupees = {
        rendez_vous["heure"]
        for rendez_vous in rendez_vous
    }

    return [
        heure
        for heure in CRENEAUX
        if heure not in heures_occupees
    ]


def administrateur_requis(fonction):
    @wraps(fonction)
    def fonction_protegee(*args, **kwargs):
        if "administrateur_id" not in session:
            return redirect(url_for("connexion_admin"))

        return fonction(*args, **kwargs)

    return fonction_protegee


@app.route("/admin/connexion", methods=["GET", "POST"])
def connexion_admin():
    if "administrateur_id" in session:
        return redirect(url_for("tableau_de_bord"))

    erreur = None

    if request.method == "POST":
        identifiant = request.form.get("identifiant", "").strip()
        mot_de_passe = request.form.get("mot_de_passe", "")

        connexion = get_db()

        administrateur = connexion.execute(
            """
            SELECT id, identifiant, mot_de_passe_hash
            FROM administrateurs
            WHERE identifiant = ?
            """,
            (identifiant,),
        ).fetchone()

        if (
            administrateur is not None
            and check_password_hash(
                administrateur["mot_de_passe_hash"],
                mot_de_passe,
            )
        ):
            session.clear()
            session["administrateur_id"] = administrateur["id"]
            session["administrateur_identifiant"] = (
                administrateur["identifiant"]
            )

            return redirect(url_for("tableau_de_bord"))

        erreur = "Identifiant ou mot de passe incorrect."

    return render_template("admin/connexion.html", erreur=erreur)


@app.route("/admin/deconnexion", methods=["POST"])
@administrateur_requis
def deconnexion_admin():
    session.clear()
    return redirect(url_for("connexion_admin"))


@app.route("/admin")
@administrateur_requis
def tableau_de_bord():
    return render_template(
        "admin/tableau_de_bord.html",
        identifiant=session.get("administrateur_identifiant"),
    )


@app.route("/")
def accueil():
    return render_template("index.html")


@app.route("/medecins")
def medecins():
    connexion = get_db()

    liste_medecins = connexion.execute(
        """
        SELECT *
        FROM medecins
        ORDER BY nom
        """
    ).fetchall()

    return render_template(
        "medecins.html",
        medecins=liste_medecins,
    )


@app.route("/medecins/<int:medecin_id>")
def detail_medecin(medecin_id):
    medecin = medecin_existe(medecin_id)

    if medecin is None:
        abort(404)

    return render_template(
        "detail_medecin.html",
        medecin=medecin,
    )


@app.route("/reservation/<int:medecin_id>", methods=["GET", "POST"])
def reservation(medecin_id):
    medecin = medecin_existe(medecin_id)

    if medecin is None:
        abort(404)

    connexion = get_db()
    valeurs = request.form if request.method == "POST" else {}
    erreur = None
    confirmation = None

    if request.method == "POST":
        nom = request.form.get("nom", "").strip()
        prenom = request.form.get("prenom", "").strip()
        telephone = telephone_valide(
            request.form.get("telephone", "")
        )
        date_naissance = request.form.get("date_naissance", "")
        ville = request.form.get("ville", "").strip()
        date_rendez_vous = request.form.get("date", "")
        heure = request.form.get("heure", "")
        motif = request.form.get("motif", "").strip()

        if not all([
            nom,
            prenom,
            telephone,
            date_naissance,
            ville,
            date_rendez_vous,
            heure,
            motif,
        ]):
            erreur = (
                "Veuillez remplir tous les champs et saisir "
                "un numéro de téléphone camerounais valide."
            )

        else:
            try:
                naissance = date.fromisoformat(date_naissance)
                date_choisie = date.fromisoformat(date_rendez_vous)
            except ValueError:
                erreur = "Veuillez saisir des dates valides."

            if erreur is None:
                if naissance >= date.today():
                    erreur = (
                        "La date de naissance doit être antérieure "
                        "à aujourd'hui."
                    )
                elif date_choisie <= date.today():
                    erreur = (
                        "Veuillez choisir une date ultérieure à aujourd'hui."
                    )
                elif heure not in CRENEAUX:
                    erreur = "Le créneau sélectionné n'est pas valide."
                elif not jour_consultation(medecin, date_choisie):
                    erreur = (
                        "Ce médecin ne consulte pas le jour choisi."
                    )

        if erreur is None:
            try:
                connexion.execute("BEGIN")

                patient = connexion.execute(
                    """
                    SELECT id
                    FROM patients
                    WHERE telephone = ?
                    """,
                    (telephone,),
                ).fetchone()

                if patient is None:
                    curseur = connexion.execute(
                        """
                        INSERT INTO patients (
                            nom,
                            prenom,
                            telephone,
                            date_naissance,
                            ville,
                            date_creation
                        )
                        VALUES (?, ?, ?, ?, ?, datetime('now', 'localtime'))
                        """,
                        (
                            nom,
                            prenom,
                            telephone,
                            date_naissance,
                            ville,
                        ),
                    )

                    patient_id = curseur.lastrowid
                else:
                    patient_id = patient["id"]

                disponibles = creneaux_disponibles(
                    medecin_id,
                    date_rendez_vous,
                )

                if heure not in disponibles:
                    connexion.rollback()
                    erreur = (
                        "Ce créneau n'est plus disponible. "
                        "Choisissez-en un autre."
                    )
                else:
                    connexion.execute(
                        """
                        INSERT INTO rendez_vous (
                            patient_id,
                            medecin_id,
                            date,
                            heure,
                            motif,
                            statut
                        )
                        VALUES (?, ?, ?, ?, ?, 'prévu')
                        """,
                        (
                            patient_id,
                            medecin_id,
                            date_rendez_vous,
                            heure,
                            motif,
                        ),
                    )

                    connexion.commit()
                    confirmation = (
                        "Votre rendez-vous a été enregistré pour le "
                        f"{date_rendez_vous} à {heure} avec {medecin['nom']}."
                    )
                    valeurs = {}

            except sqlite3.IntegrityError:
                connexion.rollback()
                erreur = (
                    "Ce créneau est déjà réservé ou les informations "
                    "ne respectent pas les règles de la base de données."
                )

            except sqlite3.Error:
                connexion.rollback()
                app.logger.exception(
                    "Erreur lors de l'enregistrement du rendez-vous."
                )
                erreur = (
                    "Une erreur technique est survenue. "
                    "Veuillez réessayer."
                )

    return render_template(
        "reservation.html",
        medecin=medecin,
        erreur=erreur,
        confirmation=confirmation,
        valeurs=valeurs,
        date_min=date.today().isoformat(),
        naissance_max=date.today().isoformat(),
    )


@app.route("/api/creneaux")
def api_creneaux():
    medecin_id = request.args.get("medecin_id", type=int)
    date_consultation = request.args.get("date")

    if medecin_id is None or not date_consultation:
        return jsonify({
            "creneaux": [],
            "message": "Choisissez un médecin et une date.",
        }), 400

    medecin = medecin_existe(medecin_id)

    if medecin is None:
        return jsonify({
            "creneaux": [],
            "message": "Médecin introuvable.",
        }), 404

    try:
        date_choisie = date.fromisoformat(date_consultation)
    except ValueError:
        return jsonify({
            "creneaux": [],
            "message": "La date indiquée est invalide.",
        }), 400

    if date_choisie <= date.today():
        return jsonify({
            "creneaux": [],
            "message": "Choisissez une date ultérieure à aujourd'hui.",
        })

    if not jour_consultation(medecin, date_choisie):
        return jsonify({
            "creneaux": [],
            "message": "Ce médecin ne consulte pas ce jour-là.",
        })

    return jsonify({
        "creneaux": creneaux_disponibles(
            medecin_id,
            date_consultation,
        ),
        "message": "Créneaux disponibles chargés.",
    })



@app.route("/api/statistiques")
def api_statistiques():
    connexion = get_db()

    # Nombre de rendez-vous par spécialité
    par_specialite = connexion.execute(
        """
        SELECT medecins.specialite, COUNT(rendez_vous.id) AS total
        FROM rendez_vous
        JOIN medecins ON rendez_vous.medecin_id = medecins.id
        GROUP BY medecins.specialite
        ORDER BY total DESC
        """
    ).fetchall()

    # Taux d'annulation pour chaque médecin
    par_medecin = connexion.execute(
        """
        SELECT
            medecins.id,
            medecins.nom,
            medecins.specialite,
            COUNT(rendez_vous.id) AS total,
            SUM(CASE WHEN rendez_vous.statut = 'annulé'
                THEN 1 ELSE 0 END) AS annules
        FROM medecins
        LEFT JOIN rendez_vous ON rendez_vous.medecin_id = medecins.id
        GROUP BY medecins.id, medecins.nom, medecins.specialite
        ORDER BY medecins.nom
        """
    ).fetchall()

    taux_annulation = []
    for medecin in par_medecin:
        total = medecin["total"]
        annules = medecin["annules"] or 0

        taux_annulation.append({
            "medecin": medecin["nom"],
            "specialite": medecin["specialite"],
            "total_rendez_vous": total,
            "rendez_vous_annules": annules,
            "taux_annulation": round(annules * 100 / total, 2)
            if total else 0
        })

    # Les cinq jours les plus chargés de chaque mois
    jours_charges = connexion.execute(
        """
        SELECT
            strftime('%Y-%m', date) AS mois,
            date,
            COUNT(*) AS total
        FROM rendez_vous
        GROUP BY mois, date
        ORDER BY mois DESC, total DESC, date ASC
        """
    ).fetchall()

    top_jours = {}
    for jour in jours_charges:
        mois = jour["mois"]
        if mois not in top_jours:
            top_jours[mois] = []

        if len(top_jours[mois]) < 5:
            top_jours[mois].append({
                "date": jour["date"],
                "total_rendez_vous": jour["total"]
            })

    # Nouveaux patients par semaine
    nouveaux_patients = connexion.execute(
        """
        SELECT
            strftime('%Y-%W', date_creation) AS semaine,
            COUNT(*) AS total
        FROM patients
        WHERE date_creation IS NOT NULL
        GROUP BY semaine
        ORDER BY semaine DESC
        """
    ).fetchall()

    connexion.close()

    return {
        "rendez_vous_par_specialite": [
            {
                "specialite": ligne["specialite"],
                "total": ligne["total"]
            }
            for ligne in par_specialite
        ],
        "taux_annulation_par_medecin": taux_annulation,
        "cinq_jours_plus_charges_par_mois": top_jours,
        "nouveaux_patients_par_semaine": [
            {
                "semaine": ligne["semaine"],
                "total": ligne["total"]
            }
            for ligne in nouveaux_patients
        ]
    }



@app.route("/mes-rendez-vous", methods=["GET", "POST"])
def mes_rendez_vous():
    rendez_vous = []
    telephone_saisi = ""
    erreur = None
    recherche_effectuee = False

    if request.method == "POST":
        recherche_effectuee = True
        telephone_saisi = request.form.get("telephone", "").strip()
        telephone = telephone_valide(telephone_saisi)

        if not telephone:
            erreur = "Veuillez saisir un numéro de téléphone camerounais valide."
        else:
            connexion = get_db()

            patient = connexion.execute(
                """
                SELECT id
                FROM patients
                WHERE telephone = ?
                """,
                (telephone,),
            ).fetchone()

            if patient is None:
                erreur = "Aucun patient ne correspond à ce numéro."
            else:
                rendez_vous = connexion.execute(
                    """
                    SELECT
                        rv.id,
                        rv.date,
                        rv.heure,
                        rv.motif,
                        rv.statut,
                        m.nom AS nom_medecin,
                        m.specialite
                    FROM rendez_vous AS rv
                    JOIN medecins AS m ON m.id = rv.medecin_id
                    WHERE rv.patient_id = ?
                    ORDER BY rv.date DESC, rv.heure DESC
                    """,
                    (patient["id"],),
                ).fetchall()

                if not rendez_vous:
                    erreur = "Aucun rendez-vous n'a été trouvé pour ce patient."
    return render_template(
        "mes_rendez_vous.html",
        rendez_vous=rendez_vous,
        telephone=telephone_saisi,
        erreur=erreur,
        recherche_effectuee=recherche_effectuee,
    )



@app.route("/admin/rendez-vous", methods=["GET", "POST"])
@administrateur_requis
def gestion_rendez_vous():
    connexion = get_db()
    erreur = None
    confirmation = None

    date_selectionnee = request.values.get(
        "date",
        date.today().isoformat(),
    )
    medecin_selectionne = request.values.get("medecin_id", "")

    try:
        date.fromisoformat(date_selectionnee)
    except ValueError:
        date_selectionnee = date.today().isoformat()
        erreur = "La date sélectionnée est invalide."

    if request.method == "POST":
        rendez_vous_id = request.form.get("rendez_vous_id", type=int)
        nouveau_statut = request.form.get("statut", "")

        if nouveau_statut not in ("effectué", "annulé"):
            erreur = "Le statut demandé n'est pas valide."

        elif rendez_vous_id is None:
            erreur = "Le rendez-vous sélectionné est invalide."

        else:
            curseur = connexion.execute(
                """
                UPDATE rendez_vous
                SET statut = ?
                WHERE id = ?
                  AND statut = 'prévu'
                """,
                (nouveau_statut, rendez_vous_id),
            )
            connexion.commit()

            if curseur.rowcount == 0:
                erreur = (
                    "Ce rendez-vous n'existe pas ou son statut "
                    "a déjà été modifié."
                )
            else:
                confirmation = (
                    "Le rendez-vous a été marqué comme "
                    f"{nouveau_statut}."
                )

    medecins = connexion.execute(
        """
        SELECT id, nom, specialite
        FROM medecins
        ORDER BY nom
        """
    ).fetchall()

    requete = """
        SELECT
            rv.id,
            rv.date,
            rv.heure,
            rv.motif,
            rv.statut,
            p.nom AS nom_patient,
            p.prenom AS prenom_patient,
            p.telephone,
            m.nom AS nom_medecin,
            m.specialite
        FROM rendez_vous AS rv
        JOIN patients AS p ON p.id = rv.patient_id
        JOIN medecins AS m ON m.id = rv.medecin_id
        WHERE rv.date = ?
    """
    parametres = [date_selectionnee]

    if medecin_selectionne:
        try:
            identifiant_medecin = int(medecin_selectionne)
        except ValueError:
            identifiant_medecin = None

        if identifiant_medecin is None:
            erreur = "Le médecin sélectionné est invalide."
            medecin_selectionne = ""
        else:
            requete += " AND rv.medecin_id = ?"
            parametres.append(identifiant_medecin)

    requete += " ORDER BY rv.heure, p.nom"

    rendez_vous = connexion.execute(
        requete,
        parametres,
    ).fetchall()

    return render_template(
        "admin/rendez_vous.html",
        rendez_vous=rendez_vous,
        medecins=medecins,
        date_selectionnee=date_selectionnee,
        medecin_selectionne=medecin_selectionne,
        erreur=erreur,
        confirmation=confirmation,
    )



@app.route("/admin/medecins", methods=["GET", "POST"])
@administrateur_requis
def gestion_medecins():
    connexion = get_db()
    erreur = None
    confirmation = None

    if request.method == "POST":
        nom = request.form.get("nom", "").strip()
        specialite = request.form.get("specialite", "").strip()
        jours_consultation = request.form.get(
            "jours_consultation", ""
        ).strip()
        photo = request.form.get("photo", "").strip()

        if not nom or not specialite or not jours_consultation:
            erreur = "Veuillez remplir tous les champs obligatoires."
        else:
            connexion.execute(
                """
                INSERT INTO medecins (
                    nom, specialite, photo, jours_consultation
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    nom,
                    specialite,
                    photo or None,
                    jours_consultation,
                ),
            )
            connexion.commit()
            confirmation = "Le médecin a été ajouté avec succès."

    medecins = connexion.execute(
        """
        SELECT id, nom, specialite, photo, jours_consultation
        FROM medecins
        ORDER BY nom
        """
    ).fetchall()

    return render_template(
        "admin/medecins.html",
        medecins=medecins,
        erreur=erreur,
        confirmation=confirmation,
    )



@app.route("/admin/medecins/<int:medecin_id>/modifier", methods=["GET", "POST"])
@administrateur_requis
def modifier_medecin(medecin_id):
    connexion = get_db()

    medecin = connexion.execute(
        """
        SELECT id, nom, specialite, photo, jours_consultation
        FROM medecins
        WHERE id = ?
        """,
        (medecin_id,),
    ).fetchone()

    if medecin is None:
        abort(404)

    erreur = None
    confirmation = None

    if request.method == "POST":
        nom = request.form.get("nom", "").strip()
        specialite = request.form.get("specialite", "").strip()
        jours_consultation = request.form.get(
            "jours_consultation", ""
        ).strip()
        photo = request.form.get("photo", "").strip()

        if not nom or not specialite or not jours_consultation:
            erreur = "Veuillez remplir tous les champs obligatoires."
        else:
            connexion.execute(
                """
                UPDATE medecins
                SET nom = ?,
                    specialite = ?,
                    photo = ?,
                    jours_consultation = ?
                WHERE id = ?
                """,
                (
                    nom,
                    specialite,
                    photo or None,
                    jours_consultation,
                    medecin_id,
                ),
            )
            connexion.commit()

            return redirect(url_for("gestion_medecins"))

    return render_template(
        "admin/modifier_medecin.html",
        medecin=medecin,
        erreur=erreur,
    )




@app.route("/admin/medecins/<int:medecin_id>/supprimer", methods=["POST"])
@administrateur_requis
def supprimer_medecin(medecin_id):
    connexion = get_db()

    medecin = connexion.execute(
        "SELECT id, nom FROM medecins WHERE id = ?",
        (medecin_id,),
    ).fetchone()

    if medecin is None:
        connexion.close()
        flash("Ce médecin n'existe pas.", "error")
        return redirect(url_for("gestion_medecins"))

    rendez_vous = connexion.execute(
        "SELECT COUNT(*) AS total FROM rendez_vous WHERE medecin_id = ?",
        (medecin_id,),
    ).fetchone()

    if rendez_vous["total"] > 0:
        connexion.close()
        flash(
            "Impossible de supprimer ce médecin : des rendez-vous "
            "sont associés à son dossier.",
            "error",
        )
        return redirect(url_for("gestion_medecins"))

    connexion.execute(
        "DELETE FROM medecins WHERE id = ?",
        (medecin_id,),
    )
    connexion.commit()
    connexion.close()

    flash(
        f"Le médecin {medecin['nom']} a été supprimé.",
        "success",
    )
    return redirect(url_for("gestion_medecins"))




@app.route("/admin/statistiques")
@administrateur_requis
def page_statistiques():
    statistiques = api_statistiques()

    return render_template("admin/statistiques.html", statistiques=statistiques)


@app.route("/test-db")
def tester_base():
    connexion = get_db()

    tables = connexion.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
    ).fetchall()

    return render_template(
        "test_db.html",
        tables=tables,
    )


@app.teardown_appcontext
def fermer_connexion(exception=None):
    connexion = g.pop("connexion", None)

    if connexion is not None:
        connexion.close()





@app.route("/admin/patients")
@administrateur_requis
def liste_patients():
    connexion = get_db()
    recherche = request.args.get("q", "").strip()

    if recherche:
        terme = f"%{recherche}%"
        patients = connexion.execute(
            """
            SELECT id, nom, prenom, telephone, date_naissance, ville
            FROM patients
            WHERE nom LIKE ?
               OR prenom LIKE ?
               OR telephone LIKE ?
            ORDER BY nom, prenom
            """,
            (terme, terme, terme),
        ).fetchall()
    else:
        patients = connexion.execute(
            """
            SELECT id, nom, prenom, telephone, date_naissance, ville
            FROM patients
            ORDER BY nom, prenom
            """
        ).fetchall()

    return render_template(
        "admin/patients.html",
        patients=patients,
        recherche=recherche,
    )


if __name__ == "__main__":
    app.run(debug=True)