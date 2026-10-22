
import sqlite3
from pathlib import Path

from flask import g


CHEMIN_BASE = Path(__file__).resolve().parent / "clinique.db"


def get_db():
    if "connexion" not in g:
        g.connexion = sqlite3.connect(CHEMIN_BASE)
        g.connexion.row_factory = sqlite3.Row
        g.connexion.execute("PRAGMA foreign_keys = ON")

    return g.connexion
