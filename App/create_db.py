# Script unique pour créer/initialiser la base

# create_db.py

import sqlite3
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "base.db")

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS chambres (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero TEXT NOT NULL,
    etat TEXT CHECK(etat IN ('libre', 'reservee', 'occupee')) NOT NULL DEFAULT 'libre',
    client TEXT,
    datetime_debut TEXT,
    datetime_fin TEXT,
    observations TEXT
)
''')

cursor.execute("SELECT COUNT(*) FROM chambres")
if cursor.fetchone()[0] == 0:
    for i in range(1, 11):
        cursor.execute("INSERT INTO chambres (numero, etat) VALUES (?, 'libre')", (f"{100+i}",))

conn.commit()
conn.close()

print("✅ Nouvelle base créée avec champs datetime et statut 'occupee'.")
