import sqlite3
import csv
import os

DB_PATH = "database.db"
CSV_PATH = "서울교통공사_지하철혼잡도정보_20250630.csv"


def create_tables_if_not_exists():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON")
    cur.execute("PRAGMA journal_mode = WAL")

    # Station 테이블
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Station (
        station_id INTEGER PRIMARY KEY AUTOINCREMENT,
        line INTEGER,
        station_number TEXT,
        station_name TEXT
    )
    """)

    # Congestion 테이블 (외래키 CASCADE)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS Congestion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        station_id INTEGER,
        day_type TEXT,
        direction TEXT,
        time_slot TEXT,
        congestion_level INTEGER,
        FOREIGN KEY(station_id) REFERENCES Station(station_id) ON DELETE CASCADE
    )
    """)

    # 인덱스 (중복 방지 및 조회 성능)
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_station_unique ON Station(line, station_number)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_congestion_unique ON Congestion(station_id, day_type, direction, time_slot)")

    conn.commit()
    conn.close()


def reset_db_from_csv():
    """
    DB의 기존 데이터를 삭제하고,
    CSV 파일 내용을 기준으로 Station과 Congestion을 다시 채운다.
    """
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"CSV 파일을 찾을 수 없습니다: {CSV_PATH}")

    create_tables_if_not_exists()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys = ON")
    cur.execute("PRAGMA journal_mode = WAL")

    # 안전하게 트랜잭션으로 처리
    try:
        # 기존 데이터 삭제 (순서: 자식 -> 부모)
        cur.execute("DELETE FROM Congestion")
        cur.execute("DELETE FROM Station")
        conn.commit()

        # CSV 읽기
        with open(CSV_PATH, encoding="cp949") as f:
            reader = csv.reader(f)
            header = next(reader)
            # 시간대 컬럼 (5번째 이후). 공백 제거한 문자열을 키로 씀
            time_slots = [c.strip().replace(" ", "") for c in header[5:]]

            for row in reader:
                if len(row) < 5:
                    continue
                day_type = row[0].strip()
                raw_line = row[1].strip()
                station_number = row[2].strip()
                station_name = row[3].strip()
                direction = row[4].strip()

                digits = ''.join(ch for ch in raw_line if ch.isdigit())
                line = int(digits) if digits else None

                # Station 삽입 (중복이면 기존 ID 가져오기)
                cur.execute("SELECT station_id FROM Station WHERE line=? AND station_number=?", (line, station_number))
                res = cur.fetchone()
                if res is None:
                    cur.execute("INSERT INTO Station (line, station_number, station_name) VALUES (?, ?, ?)",
                                (line, station_number, station_name))
                    station_id = cur.lastrowid
                else:
                    station_id = res[0]

                # Congestion 삽입
                for i, t in enumerate(time_slots):
                    idx = 5 + i
                    if idx >= len(row):
                        continue
                    raw_val = row[idx].strip()
                    if raw_val == "" or raw_val.lower() in ("na", "n/a", "-"):
                        continue
                    try:
                        val = int(round(float(raw_val.replace(",", "").replace("%", ""))))
                    except Exception:
                        continue

                    cur.execute("""
                        INSERT OR IGNORE INTO Congestion
                        (station_id, day_type, direction, time_slot, congestion_level)
                        VALUES (?, ?, ?, ?, ?)
                    """, (station_id, day_type, direction, t, val))
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    # 직접 실행 시 초기화 (테스트 용)
    print("DB 테이블 생성(없으면) 및 CSV로 초기화 시작...")
    create_tables_if_not_exists()
    reset_db_from_csv()
    print("완료.")
