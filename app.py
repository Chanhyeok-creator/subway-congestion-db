from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3

DB_PATH = "database.db"
app = Flask(__name__)
app.secret_key = "dev-secret-key"

def get_db():
    """
    안전한 DB 연결 반환.
    timeout: DB 잠금 발생 시 최대 대기 시간 (초)
    journal_mode = WAL: 동시 읽기/쓰기 성능 개선
    foreign_keys = ON: 외래키 제약 활성화
    """
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn

# 메인: 조회 (검색)
@app.route("/", methods=["GET", "POST"])
def index():
    conn = get_db()
    try:
        cursor = conn.cursor()

        # 역 목록
        cursor.execute("SELECT station_id, station_name FROM Station ORDER BY station_name")
        stations = cursor.fetchall()

        # 시간대 목록 (DB에 있는 시간대 기준)
        cursor.execute("SELECT DISTINCT time_slot FROM Congestion ORDER BY time_slot")
        time_slots = [r["time_slot"] for r in cursor.fetchall()]

        congestion_value = None

        if request.method == "POST":
            station_id = request.form.get("station")
            time_slot = request.form.get("time_slot")
            day_type = request.form.get("day_type", "평일")
            direction = request.form.get("direction", "상선")

            # 안전성: station_id가 None이면 바로 처리
            if not station_id or not time_slot:
                congestion_value = "조회 조건이 부족합니다."
            else:
                cursor.execute("""
                    SELECT congestion_level FROM Congestion
                    WHERE station_id=? AND time_slot=? AND day_type=? AND direction=?
                    LIMIT 1
                """, (station_id, time_slot, day_type, direction))
                r = cursor.fetchone()
                if r is None:
                    congestion_value = "데이터 없음"
                else:
                    congestion_value = r["congestion_level"] if r["congestion_level"] is not None else "데이터 없음"

    finally:
        conn.close()

    return render_template("index.html",
                           stations=stations,
                           time_slots=time_slots,
                           congestion_value=congestion_value)

# 추가 (새 역 + 혼잡도)
@app.route("/add_station", methods=["POST"])
def add_station():
    conn = get_db()
    try:
        cursor = conn.cursor()

        station_name = request.form.get("new_station_name", "").strip()
        new_line = request.form.get("new_line", "").strip()
        station_number = request.form.get("new_station_number", "").strip()
        day_type = request.form.get("new_day_type", "평일")
        direction = request.form.get("new_direction", "상선")

        if not station_name or not new_line or not station_number:
            flash("역 이름, 호선, 역 번호는 필수입니다.")
            return redirect(url_for("index"))

        try:
            line = int(new_line)
        except ValueError:
            flash("호선은 숫자(예: 1)로 입력하세요.")
            return redirect(url_for("index"))

        # Station 삽입 (중복이면 무시)
        cursor.execute(
            "INSERT OR IGNORE INTO Station (line, station_number, station_name) VALUES (?, ?, ?)",
            (line, station_number, station_name)
        )
        # station_id 가져오기
        cursor.execute("SELECT station_id FROM Station WHERE line=? AND station_number=?", (line, station_number))
        row = cursor.fetchone()
        if row is None:
            flash("역 추가 실패")
            return redirect(url_for("index"))
        station_id = row["station_id"]

        # 시간대 목록: 현재 DB에 존재하는 시간대 기준으로 입력받음
        cursor.execute("SELECT DISTINCT time_slot FROM Congestion ORDER BY time_slot")
        time_slots = [r["time_slot"] for r in cursor.fetchall()]

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
        flash("새로운 역과 혼잡도 추가 완료")
    except sqlite3.Error as e:
        conn.rollback()
        flash(f"추가 중 오류 발생: {e}")
    finally:
        conn.close()

    return redirect(url_for("index"))

# 역 전체 삭제
@app.route("/delete_station", methods=["POST"])
def delete_station():
    conn = get_db()
    try:
        cursor = conn.cursor()
        station_id = request.form.get("del_station")
        if not station_id:
            flash("삭제할 역을 선택하세요.")
            return redirect(url_for("index"))

        try:
            # 1) 자식(혼잡도) 삭제
            cursor.execute("DELETE FROM Congestion WHERE station_id=?", (station_id,))
            # 2) 부모(역) 삭제
            cursor.execute("DELETE FROM Station WHERE station_id=?", (station_id,))
            conn.commit()
            flash("선택한 역과 관련 혼잡도 모두 삭제되었습니다.")
        except sqlite3.Error as e:
            conn.rollback()
            flash(f"삭제 중 오류 발생: {e}")

    finally:
        conn.close()

    return redirect(url_for("index"))

# 특정 혼잡도 삭제
@app.route("/delete_congestion", methods=["POST"])
def delete_congestion():
    conn = get_db()
    try:
        cursor = conn.cursor()
        station_id = request.form.get("del_station")
        time_slot = request.form.get("del_time")
        day_type = request.form.get("del_day_type", "평일")
        direction = request.form.get("del_direction", "상선")

        if not station_id or not time_slot:
            flash("역과 시간대를 선택하세요.")
            return redirect(url_for("index"))

        try:
            cursor.execute("""
                DELETE FROM Congestion
                WHERE station_id=? AND time_slot=? AND day_type=? AND direction=?
            """, (station_id, time_slot, day_type, direction))
            conn.commit()
            flash("선택한 혼잡도 데이터가 삭제되었습니다.")
        except sqlite3.Error as e:
            conn.rollback()
            flash(f"삭제 중 오류 발생: {e}")

    finally:
        conn.close()

    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=False)