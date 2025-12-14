from flask import Flask, render_template, request
import sqlite3

DB_PATH = "database.db"
app = Flask(__name__)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/", methods=["GET", "POST"])
def index():
    conn = get_db()
    cursor = conn.cursor()

    # 역 목록 가져오기
    cursor.execute("SELECT station_id, station_name FROM Station ORDER BY station_name")
    stations = cursor.fetchall()

    # 시간대 목록 가져오기
    cursor.execute("SELECT DISTINCT time_slot FROM Congestion ORDER BY time_slot")
    time_slots = [row["time_slot"] for row in cursor.fetchall()]

    congestion_value = None

    if request.method == "POST":
        station_id = request.form.get("station")
        time_slot = request.form.get("time_slot")
        day_type = request.form.get("day_type") or "평일"   # 기본 평일
        direction = request.form.get("direction") or "상선" # 기본 상선

        # 선택된 값으로 Congestion 조회
        cursor.execute("""
            SELECT congestion_level FROM Congestion
            WHERE station_id=? AND time_slot=? AND day_type=? AND direction=? LIMIT 1
        """, (station_id, time_slot, day_type, direction))
        result = cursor.fetchone()
        if result:
            congestion_value = result["congestion_level"]

    conn.close()
    return render_template("index.html",
                           stations=stations,
                           time_slots=time_slots,
                           congestion_value=congestion_value)

if __name__ == "__main__":
    app.run(debug=True)
