from flask import Flask, render_template, request
import sqlite3

DB_PATH = "database.db"

app = Flask(__name__)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def index():
    return render_template("index.html", congestion=None, searched=False)

@app.route("/search", methods=["POST"])
def search():
    station_name = request.form["station_name"]
    day_type = request.form["day_type"]
    direction = request.form["direction"]
    time_slot = request.form["time_slot"]

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT C.congestion_level
        FROM Congestion C
        JOIN Station S ON C.station_id = S.station_id
        WHERE S.station_name = ?
          AND C.day_type = ?
          AND C.direction = ?
          AND C.time_slot = ?
    """, (station_name, day_type, direction, time_slot))

    row = cursor.fetchone()
    conn.close()

    if row:
        congestion = row["congestion_level"]
    else:
        congestion = None

    return render_template(
        "index.html",
        congestion=congestion,
        searched=True
    )

if __name__ == "__main__":
    app.run(debug=True)
