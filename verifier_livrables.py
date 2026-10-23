
import sqlite3
from pathlib import Path

chemin_base = Path("database/clinique.db")

connexion = sqlite3.connect(chemin_base)
connexion.row_factory = sqlite3.Row

try:
    tables = connexion.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
    """).fetchall()

    print("TABLES PRÉSENTES")
    for table in tables:
        nom_table = table["name"]
        print(f"\n{nom_table}")

        nombre = connexion.execute(
            f'SELECT COUNT(*) FROM "{nom_table}"'
        ).fetchone()[0]

        print(f"Nombre d'enregistrements : {nombre}")

finally:
    connexion.close()
