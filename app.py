from flask import Flask, render_template, request
import sqlite3

DB_PATH = "database.db"
app = Flask(__name__)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# 조회 기능
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
        day_type = request.form.get("day_type") or "평일"
        direction = request.form.get("direction") or "상선"

        # 선택된 값으로 혼잡도 조회
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

# 새로운 역 + 혼잡도 추가 기능
@app.route("/add_station", methods=["POST"])
def add_station():
    conn = get_db()
    cursor = conn.cursor()

    station_name = request.form.get("new_station_name")
    line = request.form.get("new_line")
    station_number = request.form.get("new_station_number")
    day_type = request.form.get("new_day_type") or "평일"
    direction = request.form.get("new_direction") or "상선"

    try:
        line = int(line)
    except ValueError:
        line = None

    # Station 테이블에 INSERT
    cursor.execute("SELECT station_id FROM Station WHERE line=? AND station_number=?", (line, station_number))
    res = cursor.fetchone()
    if res is None:
        cursor.execute(
            "INSERT INTO Station (line, station_number, station_name) VALUES (?, ?, ?)",
            (line, station_number, station_name)
        )
        station_id = cursor.lastrowid
    else:
        station_id = res["station_id"]

    # 시간대별 혼잡도 INSERT
    cursor.execute("SELECT DISTINCT time_slot FROM Congestion ORDER BY time_slot")
    time_slots = [row["time_slot"] for row in cursor.fetchall()]

    for t in time_slots:
        val = request.form.get(f"time_{t}")
        if val is not None and val != "":
            try:
                congestion_level = int(val)
                cursor.execute("""
                    INSERT OR IGNORE INTO Congestion (station_id, day_type, direction, time_slot, congestion_level)
                    VALUES (?, ?, ?, ?, ?)
                """, (station_id, day_type, direction, t, congestion_level))
            except ValueError:
                continue

    conn.commit()
    conn.close()
    return "새로운 역과 혼잡도가 추가되었습니다. <a href='/'>홈으로</a>"

if __name__ == "__main__":
    app.run(debug=True)
