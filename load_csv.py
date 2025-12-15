import sqlite3
import csv

DB_PATH = "database.db"
CSV_PATH = "서울교통공사_지하철혼잡도정보_20250630.csv"

# DB 연결
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
print("DB 연결 완료")

# SQLite 안정화 설정
cursor.execute("PRAGMA foreign_keys = ON")
cursor.execute("PRAGMA journal_mode = WAL")

# Station 테이블
cursor.execute("""
CREATE TABLE IF NOT EXISTS Station (
    station_id INTEGER PRIMARY KEY AUTOINCREMENT,
    line INTEGER,
    station_number TEXT,
    station_name TEXT
)
""")

# Congestion 테이블 (CASCADE 적용!)
cursor.execute("""
CREATE TABLE IF NOT EXISTS Congestion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id INTEGER,
    day_type TEXT,
    direction TEXT,
    time_slot TEXT,
    congestion_level INTEGER,
    FOREIGN KEY(station_id)
        REFERENCES Station(station_id)
        ON DELETE CASCADE
)
""")

# 인덱스
cursor.execute("""
CREATE UNIQUE INDEX IF NOT EXISTS idx_station_unique
ON Station(line, station_number)
""")

cursor.execute("""
CREATE UNIQUE INDEX IF NOT EXISTS idx_congestion_unique
ON Congestion(station_id, day_type, direction, time_slot)
""")

conn.commit()
print("테이블 생성 완료")

# CSV 로드
with open(CSV_PATH, encoding="cp949") as csv_file:
    csv_reader = csv.reader(csv_file)
    header = next(csv_reader)
    time_slots = [c.strip().replace(" ", "") for c in header[5:]]

    for row in csv_reader:
        day_type = row[0].strip()
        raw_line = row[1].strip()
        station_number = row[2].strip()
        station_name = row[3].strip()
        direction = row[4].strip()

        digits = ''.join(ch for ch in raw_line if ch.isdigit())
        line = int(digits) if digits else None

        # Station
        cursor.execute(
            "SELECT station_id FROM Station WHERE line=? AND station_number=?",
            (line, station_number)
        )
        res = cursor.fetchone()
        if res is None:
            cursor.execute(
                "INSERT INTO Station (line, station_number, station_name) VALUES (?, ?, ?)",
                (line, station_number, station_name)
            )
            station_id = cursor.lastrowid
        else:
            station_id = res[0]

        # Congestion
        for i, time_slot in enumerate(time_slots):
            idx = 5 + i
            if idx >= len(row):
                continue

            raw = row[idx].strip()
            if raw in ("", "na", "n/a", "-"):
                continue

            try:
                congestion_level = int(round(float(raw.replace(",", "").replace("%", ""))))
            except ValueError:
                continue

            cursor.execute("""
                INSERT OR IGNORE INTO Congestion
                (station_id, day_type, direction, time_slot, congestion_level)
                VALUES (?, ?, ?, ?, ?)
            """, (station_id, day_type, direction, time_slot, congestion_level))

conn.commit()
conn.close()
print("CSV 로드 완료")