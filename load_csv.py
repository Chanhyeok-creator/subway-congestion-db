import sqlite3
import csv

DB_PATH = "database.db"
CSV_PATH = "서울교통공사_지하철혼잡도정보_20250630.csv"

# 1. 데이터베이스 연결
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
print("데이터베이스 연결 완료됨")

# 2. Station 테이블 생성
cursor.execute("""
CREATE TABLE IF NOT EXISTS Station (
    station_id INTEGER PRIMARY KEY AUTOINCREMENT,
    line INTEGER,
    station_number TEXT,
    station_name TEXT
)
""")
print("Station 테이블 생성 완료됨")

# 3. Congestion 테이블 생성
cursor.execute("""
CREATE TABLE IF NOT EXISTS Congestion (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id INTEGER,
    day_type TEXT,
    direction TEXT,
    time_slot TEXT,
    congestion_level INTEGER,
    FOREIGN KEY(station_id) REFERENCES Station(station_id)
)
""")
print("Congestion 테이블 생성 완료됨")

conn.commit()

# 4. CSV 열기
try:
    csv_file = open(CSV_PATH, encoding="cp949")
except FileNotFoundError:
    print(f"오류 발생: CSV 파일을 찾을 수 없음: {CSV_PATH}")
    conn.close()
    raise

csv_reader = csv.reader(csv_file)
header = next(csv_reader)
print("CSV header는?:")
print(header)

# 5. CSV → Station INSERT
insert_count = 0
row_count = 0
BATCH_COMMIT = 200

for row in csv_reader:
    row_count += 1
    try:
        raw_line = row[1].strip()
        station_number = row[2].strip()
        station_name = row[3].strip()
    except IndexError:
        print(f"데이터 행 인덱스 오류: 행 번호 = {row_count}")
        continue

    # 호선 숫자 추출
    line = None
    digits = ''.join(ch for ch in raw_line if ch.isdigit())
    if digits != "":
        line = int(digits)

    # 이미 존재하는지 확인
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
        insert_count += 1

        if insert_count % 10 == 0:
            print(f"Station 추가 중... 현재까지 추가된 역 수: {insert_count}")

    # 배치 커밋
    if insert_count > 0 and insert_count % BATCH_COMMIT == 0:
        conn.commit()
        print(f"중간 commit 완료 (총 {insert_count}개 역 저장)")

# 6. 최종 커밋
conn.commit()
print("모든 insert commit 완료")

# 7. 결과 확인
cursor.execute("SELECT COUNT(*) FROM Station")
total_station = cursor.fetchone()[0]
print(f"Station 테이블 총 레코드 수: {total_station}")
print(f"이번 실행에서 추가된 역 수: {insert_count}")
print(f"CSV에서 읽은 전체 행 수: {row_count}")

csv_file.close()
conn.close()
print("DB 연결 종료")
