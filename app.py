from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3

DB_PATH = "database.db"
app = Flask(__name__)
app.secret_key = "dev-secret-key"


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


# 메인: 조회
@app.route("/", methods=["GET", "POST"])
def index():
    conn = get_db()
    try:
        cursor = conn.cursor()

        # 역 목록
        cursor.execute("SELECT station_id, station_name FROM Station ORDER BY station_name")
        stations = cursor.fetchall()

        # 시간대 목록
        cursor.execute("SELECT DISTINCT time_slot FROM Congestion ORDER BY time_slot")
        time_slots = [r["time_slot"] for r in cursor.fetchall()]

        result = None

        if request.method == "POST":
            station_id = request.form.get("station")
            time_slot = request.form.get("time_slot")
            day_type = request.form.get("day_type", "평일")
            direction = request.form.get("direction", "상선")

            if station_id and time_slot:
                cursor.execute("""
                    SELECT s.station_name, c.day_type, c.time_slot, c.direction, c.congestion_level
                    FROM Congestion c
                    JOIN Station s ON c.station_id = s.station_id
                    WHERE c.station_id=? AND c.time_slot=? AND c.day_type=? AND c.direction=?
                    LIMIT 1
                """, (station_id, time_slot, day_type, direction))
                row = cursor.fetchone()
                if row:
                    result = {
                        "station_name": row["station_name"],
                        "day_type": row["day_type"],
                        "time_slot": row["time_slot"],
                        "direction": row["direction"],
                        "congestion_level": row["congestion_level"]
                    }
                else:
                    # 데이터 없으면 역이름만 가져와 표시
                    cursor.execute("SELECT station_name FROM Station WHERE station_id=?", (station_id,))
                    s = cursor.fetchone()
                    result = {
                        "station_name": s["station_name"] if s else "",
                        "day_type": day_type,
                        "time_slot": time_slot,
                        "direction": direction,
                        "congestion_level": None
                    }

    finally:
        conn.close()

    return render_template("index.html",
                           stations=stations,
                           time_slots=time_slots,
                           result=result)


# Create: 추가 (새 역 + 혼잡도)
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

        cursor.execute("INSERT OR IGNORE INTO Station (line, station_number, station_name) VALUES (?, ?, ?)",
                       (line, station_number, station_name))

        cursor.execute("SELECT station_id FROM Station WHERE line=? AND station_number=?", (line, station_number))
        row = cursor.fetchone()
        if row is None:
            flash("역 추가 실패")
            return redirect(url_for("index"))
        station_id = row["station_id"]

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


# Update: 역 정보 수정
@app.route("/update_station", methods=["POST"])
def update_station():
    conn = get_db()
    try:
        cursor = conn.cursor()

        station_id = request.form.get("upd_station")
        new_name = request.form.get("upd_station_name", "").strip()
        new_line = request.form.get("upd_line", "").strip()
        new_number = request.form.get("upd_station_number", "").strip()

        if not station_id:
            flash("수정할 역을 선택하세요.")
            return redirect(url_for("index"))

        # Build update parts
        updates = []
        params = []
        if new_name != "":
            updates.append("station_name=?")
            params.append(new_name)
        if new_line != "":
            try:
                ln = int(new_line)
                updates.append("line=?")
                params.append(ln)
            except ValueError:
                flash("호선은 숫자(예: 1)로 입력하세요.")
                return redirect(url_for("index"))
        if new_number != "":
            updates.append("station_number=?")
            params.append(new_number)

        if not updates:
            flash("변경할 값을 하나 이상 입력하세요.")
            return redirect(url_for("index"))

        params.append(station_id)
        sql = "UPDATE Station SET " + ", ".join(updates) + " WHERE station_id=?"
        try:
            cursor.execute(sql, tuple(params))
            conn.commit()
            flash("역 정보가 수정되었습니다.")
        except sqlite3.Error as e:
            conn.rollback()
            flash(f"역 수정 중 오류 발생: {e}")

    finally:
        conn.close()

    return redirect(url_for("index"))


# Update: 특정 혼잡도 수정
@app.route("/update_congestion", methods=["POST"])
def update_congestion():
    conn = get_db()
    try:
        cursor = conn.cursor()
        station_id = request.form.get("upd_station2")
        time_slot = request.form.get("upd_time")
        day_type = request.form.get("upd_day_type", "평일")
        direction = request.form.get("upd_direction", "상선")
        new_val = request.form.get("upd_value", "").strip()  # 빈문자열이면 NULL로 설정

        if not station_id or not time_slot:
            flash("역과 시간대를 선택하세요.")
            return redirect(url_for("index"))

        if new_val == "":
            # set NULL
            try:
                cursor.execute("""
                    UPDATE Congestion
                    SET congestion_level = NULL
                    WHERE station_id=? AND time_slot=? AND day_type=? AND direction=?
                """, (station_id, time_slot, day_type, direction))
                conn.commit()
                flash("혼잡도 값이 NULL로 설정되었습니다.")
            except sqlite3.Error as e:
                conn.rollback()
                flash(f"업데이트 중 오류 발생: {e}")
        else:
            # try to convert to int
            try:
                new_int = int(new_val)
            except ValueError:
                flash("새 혼잡도 값은 정수로 입력하세요.")
                return redirect(url_for("index"))

            try:
                cursor.execute("""
                    UPDATE Congestion
                    SET congestion_level = ?
                    WHERE station_id=? AND time_slot=? AND day_type=? AND direction=?
                """, (new_int, station_id, time_slot, day_type, direction))
                if cursor.rowcount == 0:
                    # no existing row: insert new record
                    cursor.execute("""
                        INSERT INTO Congestion (station_id, day_type, direction, time_slot, congestion_level)
                        VALUES (?, ?, ?, ?, ?)
                    """, (station_id, day_type, direction, time_slot, new_int))
                conn.commit()
                flash("혼잡도 값이 수정되었습니다.")
            except sqlite3.Error as e:
                conn.rollback()
                flash(f"업데이트 중 오류 발생: {e}")

    finally:
        conn.close()

    return redirect(url_for("index"))


# Delete: 역 전체 삭제
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
            cursor.execute("DELETE FROM Congestion WHERE station_id=?", (station_id,))
            cursor.execute("DELETE FROM Station WHERE station_id=?", (station_id,))
            conn.commit()
            flash("선택한 역과 관련 혼잡도 모두 삭제되었습니다.")
        except sqlite3.Error as e:
            conn.rollback()
            flash(f"삭제 중 오류 발생: {e}")

    finally:
        conn.close()

    return redirect(url_for("index"))


# Delete: 특정 혼잡도 삭제
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
