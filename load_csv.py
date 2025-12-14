import sqlite3
import csv

DB_PATH = "database.db"
CSV_PATH = "서울교통공사_지하철혼잡도정보_20250630.csv"

# 1) DB 연결
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
print("DB 연결 완료")

# 외래키 사용
cursor.execute("PRAGMA foreign_keys = ON")

# 2) 테이블 생성
cursor.execute("""
CREATE TABLE IF NOT EXISTS Station (
    station_id INTEGER PRIMARY KEY AUTOINCREMENT,
    line INTEGER,
    station_number TEXT,
    station_name TEXT
)
""")

cursor.execute("""
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

# 중복 방지 인덱스
cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_station_unique ON Station(line, station_number)")
cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_congestion_unique ON Congestion(station_id, day_type, direction, time_slot)")

conn.commit()
print("테이블 및 인덱스 생성 완료")

# 3) CSV 열기
try:
    csv_file = open(CSV_PATH, encoding="cp949")
except FileNotFoundError:
    print(f"CSV 파일 없음: {CSV_PATH}")
    conn.close()
    raise

csv_reader = csv.reader(csv_file)
header = next(csv_reader)
time_slots = [col.strip().replace(" ", "") for col in header[5:]]

# 4) CSV 행 순회
for row in csv_reader:
    day_type = row[0].strip()
    raw_line = row[1].strip()
    station_number = row[2].strip()
    station_name = row[3].strip()
    direction = row[4].strip()

    digits = ''.join(ch for ch in raw_line if ch.isdigit())
    line = int(digits) if digits else None

    # Station 추가
    cursor.execute("SELECT station_id FROM Station WHERE line=? AND station_number=?", (line, station_number))
    res = cursor.fetchone()
    if res is None:
        cursor.execute("INSERT INTO Station (line, station_number, station_name) VALUES (?, ?, ?)",
                       (line, station_number, station_name))
        station_id = cursor.lastrowid
    else:
        station_id = res[0]

    # Congestion 추가
    for i, time_slot in enumerate(time_slots):
        col_idx = 5 + i
        if col_idx >= len(row): continue
        raw_value = row[col_idx].strip()
        if raw_value == "" or raw_value.lower() in ("na", "n/a", "-"): continue
        cleaned = raw_value.replace(",", "").replace("%", "").strip()
        try:
            congestion_level = int(round(float(cleaned)))
        except ValueError:
            continue

        cursor.execute("""
            INSERT OR IGNORE INTO Congestion (station_id, day_type, direction, time_slot, congestion_level)
            VALUES (?, ?, ?, ?, ?)
        """, (station_id, day_type, direction, time_slot, congestion_level))

conn.commit()
csv_file.close()
conn.close()
print("CSV 로드 완료")
