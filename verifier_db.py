
import sqlite3

connexion = sqlite3.connect("database/clinique.db")

requete = """
SELECT name
FROM sqlite_master
WHERE type = 'table'
AND name NOT LIKE 'sqlite_%'
ORDER BY name;
"""

tables = connexion.execute(requete).fetchall()

print("Tables présentes dans la base de données :")

for table in tables:
    print("-", table[0])

connexion.close()
