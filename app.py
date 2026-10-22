from flask import Flask, g, render_template, abort
from flask import Flask, g, render_template

from database.db import get_db

app = Flask(__name__)


@app.route("/")
def accueil():
    return render_template("index.html")


@app.route("/medecins")
def medecins():
    connexion = get_db()

    liste_medecins = connexion.execute("""
        SELECT *
        FROM medecins
        ORDER BY nom
    """).fetchall()

    return render_template(
        "medecins.html",
        medecins=liste_medecins
    )


@app.route("/mes-rendez-vous")
def mes_rendez_vous():
    return render_template("mes_rendez_vous.html")


@app.route("/test-db")
def tester_base():
    connexion = get_db()

    tables = connexion.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """).fetchall()

    return render_template("test_db.html", tables=tables)


@app.teardown_appcontext
def fermer_connexion(exception=None):
    connexion = g.pop("connexion", None)

    if connexion is not None:
        connexion.close()


@app.route("/medecins/<int:medecin_id>")
def detail_medecin(medecin_id):
    connexion = get_db()

    medecin = connexion.execute("""
        SELECT *
        FROM medecins
        WHERE id = ?
    """, (medecin_id,)).fetchone()

    if medecin is None:
        abort(404)

    return render_template(
        "detail_medecin.html",
        medecin=medecin
    )



if __name__ == "__main__":
    app.run(debug=True)


