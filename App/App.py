from flask import Flask, render_template, request, redirect, url_for, flash
#import sqlite3
import psycopg2
import psycopg2.extras

import os
DATABASE_URL = os.environ.get("DATABASE_URL")  # sera défini via Render

from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "secret123"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "base.db")


ETAT_LIBELLES = {
    "libre": "Libre",
    "reservee": "Réservée",
    "occupee": "Occupée"
}


def format_duree(delta):
    total_seconds = int(delta.total_seconds())
    heures = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{heures}h{minutes:02d}"


def get_chambres():
    now = datetime.now()

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("SELECT * FROM chambres")
    rows = cursor.fetchall()
    conn.close()

    chambres = []
    for row in rows:
        c = dict(row)
        debut = datetime.fromisoformat(c["datetime_debut"]) if c["datetime_debut"] else None
        fin = datetime.fromisoformat(c["datetime_fin"]) if c["datetime_fin"] else None

        c["debut_affichage"] = debut.strftime("%d/%m/%Y à %H:%M") if debut else ""
        c["fin_affichage"] = fin.strftime("%d/%m/%Y à %H:%M") if fin else ""
        c["etat_libelle"] = ETAT_LIBELLES.get(c["etat"], c["etat"])

        c["status_color"] = "lightgray"
        c["temps_restant"] = ""
        c["depassé"] = False

        if c["etat"] == "libre":
            c["status_color"] = "lightgreen"

        elif c["etat"] == "reservee":
            if debut and fin:
                if fin < now:
                    c["status_color"] = "lightblue"
                    c["depassé"] = True
                elif debut <= now <= fin:
                    c["status_color"] = "gray"
                    delta = fin - now
                    c["temps_restant"] = format_duree(delta)

        elif c["etat"] == "occupee":
            if debut and fin:
                if now <= fin:
                    c["status_color"] = "orange"
                    delta = fin - now
                    c["temps_restant"] = format_duree(delta)
                else:
                    c["status_color"] = "red"
                    c["depassé"] = True

        chambres.append(c)
    return chambres


@app.route('/')
def index():
    chambres = get_chambres()
    return render_template('index.html', chambres=chambres)


@app.route('/reserver/<int:id>', methods=['GET', 'POST'])
def reserver(id):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)



    if request.method == 'POST':
        client = request.form['client']
        debut = request.form['datetime_debut']
        fin = request.form['datetime_fin']
        etat = request.form['etat']
        observations = request.form.get('observations', '')

        cursor.execute('''
            UPDATE chambres SET client = ?, datetime_debut = ?, datetime_fin = ?, etat = ?, observations = ?
            WHERE id = ?
        ''', (client, debut, fin, etat, observations, id))
        conn.commit()
        flash("✅ Réservation enregistrée avec succès.")
        conn.close()
        return redirect(url_for('index'))

    cursor.execute("SELECT * FROM chambres WHERE id = ?", (id,))
    chambre = cursor.fetchone()
    conn.close()
    return render_template("reservation.html", chambre=chambre)


@app.route('/liberer/<int:id>', methods=['POST'])
def liberer(id):


    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE chambres SET
            etat = 'libre',
            client = NULL,
            datetime_debut = NULL,
            datetime_fin = NULL,
            observations = NULL
        WHERE id = %s
    ''', (id,))

    conn.commit()
    conn.close()
    flash(f"✅ Chambre {id} libérée.")
    return redirect(url_for('index'))


@app.route('/reservation-rapide/<int:id>', methods=['POST'])
def reservation_rapide(id):
    client = request.form['client']
    heure_debut = request.form['heure_debut']
    heure_fin = request.form['heure_fin']
    today = datetime.now().strftime("%Y-%m-%d")
    datetime_debut_str = f"{today}T{heure_debut}"
    datetime_fin_str = f"{today}T{heure_fin}"

    try:
        datetime_debut = datetime.fromisoformat(datetime_debut_str)
        datetime_fin = datetime.fromisoformat(datetime_fin_str)
    except ValueError:
        flash("❌ Heures incorrectes.")
        return redirect(url_for('index'))

    now = datetime.now()
    delay = (datetime_debut - now).total_seconds() / 60  # minutes
    etat = "occupee" if delay <= 30 else "reservee"

    heure_min = datetime.strptime("06:00", "%H:%M").time()
    heure_max = datetime.strptime("23:59", "%H:%M").time()
    h_debut = datetime.strptime(heure_debut, "%H:%M").time()
    h_fin = datetime.strptime(heure_fin, "%H:%M").time()

    if not (heure_min <= h_debut <= heure_max and heure_min <= h_fin <= heure_max):
        flash("❌ Pour cet horaire, utilisez le bouton 'Réserver' classique.")
        return redirect(url_for('index'))

    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE chambres SET
            client = %s,
            datetime_debut = %s,
            datetime_fin = %s,
            etat = %s
        WHERE id = %s
    ''', (client, datetime_debut_str, datetime_fin_str, etat, id))

    conn.commit()
    conn.close()


    flash(f"✅ Réservation rapide enregistrée ({etat}).")
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
