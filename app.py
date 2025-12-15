from flask import Flask, render_template, request
import sqlite3

DB_PATH = "database.db"
app = Flask(__name__)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # 외래키 활성화 (CASCADE)
    return conn

# 조회
@app.route("/", methods=["GET", "POST"])
def index():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT station_id, station_name FROM Station ORDER BY station_name")
    stations = cursor.fetchall()

    cursor.execute("SELECT DISTINCT time_slot FROM Congestion ORDER BY time_slot")
    time_slots = [row["time_slot"] for row in cursor.fetchall()]

    congestion_value = None

    if request.method == "POST":
        station_id = request.form.get("station")
        time_slot = request.form.get("time_slot")
        day_type = request.form.get("day_type") or "평일"
        direction = request.form.get("direction") or "상선"

        cursor.execute("""
            SELECT congestion_level FROM Congestion
            WHERE station_id=? AND time_slot=? AND day_type=? AND direction=? LIMIT 1
        """, (station_id, time_slot, day_type, direction))
        result = cursor.fetchone()
        if result:
            congestion_value = result["congestion_level"] if result["congestion_level"] is not None else "데이터 없음"

    conn.close()
    return render_template("index.html",
                           stations=stations,
                           time_slots=time_slots,
                           congestion_value=congestion_value)

# 추가
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

    cursor.execute("SELECT station_id FROM Station WHERE line=? AND station_number=?", (line, station_number))
    res = cursor.fetchone()
    if res is None:
        cursor.execute("INSERT INTO Station (line, station_number, station_name) VALUES (?, ?, ?)",
                       (line, station_number, station_name))
        station_id = cursor.lastrowid
    else:
        station_id = res["station_id"]

    cursor.execute("SELECT DISTINCT time_slot FROM Congestion ORDER BY time_slot")
    time_slots = [row["time_slot"] for row in cursor.fetchall()]

    for t in time_slots:
        val = request.form.get(f"time_{t}")
        if val is None or val == "":
            congestion_level = None
        else:
            try:
                congestion_level = int(val)
            except ValueError:
                congestion_level = None

        cursor.execute("""
            INSERT OR IGNORE INTO Congestion (station_id, day_type, direction, time_slot, congestion_level)
            VALUES (?, ?, ?, ?, ?)
        """, (station_id, day_type, direction, t, congestion_level))

    conn.commit()
    conn.close()
    return "추가 완료. <a href='/'>홈으로</a>"

# 역 전체 삭제
@app.route("/delete_station", methods=["POST"])
def delete_station():
    conn = get_db()
    cursor = conn.cursor()
    station_id = request.form.get("del_station")
    cursor.execute("DELETE FROM Station WHERE station_id=?", (station_id,))
    conn.commit()
    conn.close()
    return "역과 관련 혼잡도 삭제 완료. <a href='/'>홈으로</a>"

# 특정 혼잡도 삭제
@app.route("/delete_congestion", methods=["POST"])
def delete_congestion():
    conn = get_db()
    cursor = conn.cursor()
    station_id = request.form.get("del_station")
    time_slot = request.form.get("del_time")
    day_type = request.form.get("del_day_type") or "평일"
    direction = request.form.get("del_direction") or "상선"

    cursor.execute("""
        DELETE FROM Congestion
        WHERE station_id=? AND time_slot=? AND day_type=? AND direction=?
    """, (station_id, time_slot, day_type, direction))

    conn.commit()
    conn.close()
    return "혼잡도 데이터 삭제 완료. <a href='/'>홈으로</a>"

if __name__ == "__main__":
    app.run(debug=True)
