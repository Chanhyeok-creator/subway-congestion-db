import sqlite3
import csv

DB_PATH = "database.db"
CSV_PATH = "서울교통공사_지하철혼잡도정보_20250630.csv"  # 필요하면 파일명 수정

# 1) DB 연결 및 설정
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
print("데이터베이스 연결 완료됨")

# 외래키 사용 설정 (SQLite 특성)
cursor.execute("PRAGMA foreign_keys = ON")

# 2) 테이블 생성 (있으면 건너뜀)
cursor.execute("""
CREATE TABLE IF NOT EXISTS Station (
    station_id INTEGER PRIMARY KEY AUTOINCREMENT,
    line INTEGER,
    station_number TEXT,
    station_name TEXT
)
""")
print("Station 테이블 생성 완료됨")

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

# 성능을 위해(중복방지) 인덱스 생성 (처음에만 효과)
cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_station_unique ON Station(line, station_number)")
# Congestion의 중복을 DB 수준에서 막기 위한 유니크 인덱스 (이미 데이터가 있으면 실패할 수 있으니 IF NOT EXISTS 사용)
cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_congestion_unique ON Congestion(station_id, day_type, direction, time_slot)")

conn.commit()
print("테이블 스키마 및 인덱스 저장 완료")


# 3) CSV 열기
try:
    csv_file = open(CSV_PATH, encoding="cp949")
except FileNotFoundError:
    print(f"오류: CSV 파일을 찾을 수 없습니다: {CSV_PATH}")
    conn.close()
    raise

csv_reader = csv.reader(csv_file)
header = next(csv_reader)
print("CSV 헤더:")
print(header)

# 시간대 컬럼(5번째 인덱스 이후) 정리: 공백 제거 등
time_slots = [col.strip().replace(" ", "") for col in header[5:]]
print(f"인식된 시간대 개수: {len(time_slots)}")


# 4) CSV 행 순회하면서 Station 추가 및 Congestion 삽입
station_new_count = 0
congestion_insert_count = 0
row_count = 0

# 배치 커밋 단위 (너무 자주 커밋하면 느림)
STATION_BATCH = 200
CONGESTION_BATCH = 1000

for row in csv_reader:
    row_count += 1
    # CSV 기본 컬럼: 0:요일구분,1:호선,2:역번호,3:출발역,4:상하구분,5~:시간별값
    try:
        day_type = row[0].strip()         # 평일/토요일/일요일
        raw_line = row[1].strip()         # '1호선' 등
        station_number = row[2].strip()
        station_name = row[3].strip()
        direction = row[4].strip()        # 상선/하선
    except IndexError:
        print(f"경고: 데이터 행 인덱스 오류 (스킵): 행번호={row_count}")
        continue

    # 호선 숫자 추출 (ex; '1호선' -> 1)
    digits = ''.join(ch for ch in raw_line if ch.isdigit())
    line = int(digits) if digits != "" else None

    # 1) Station 존재 확인, 없으면 INSERT
    cursor.execute("SELECT station_id FROM Station WHERE line=? AND station_number=?", (line, station_number))
    res = cursor.fetchone()
    if res is None:
        cursor.execute("INSERT INTO Station (line, station_number, station_name) VALUES (?, ?, ?)",
                       (line, station_number, station_name))
        station_new_count += 1
        # 마지막에 삽입된 station_id 가져오기(필요할 시 사용 가능)
        station_id = cursor.lastrowid
        if station_new_count % 10 == 0:
            print(f"Station 추가 중... 지금까지 추가된 신규 역 수: {station_new_count}")
    else:
        station_id = res[0]

    # 배치 커밋 (Station)
    if station_new_count > 0 and station_new_count % STATION_BATCH == 0:
        conn.commit()
        print(f"중간 커밋(Station): 총 {station_new_count}개 신규 역 저장")

    # 2) Congestion 삽입: 시간대별로 반복
    for i, time_slot in enumerate(time_slots):
        # CSV에서 해당 시간값 위치: 5 + i
        col_idx = 5 + i
        if col_idx >= len(row):
            # CSV 열 수가 모자란 경우 스킵
            continue
        raw_value = row[col_idx].strip()
        if raw_value == "" or raw_value.lower() in ("na", "n/a", "-"):
            # 값 없는 경우 건너뜀
            continue

        # 숫자 전처리: 쉼표/퍼센트 제거, 공백 제거함
        cleaned = raw_value.replace(",", "").replace("%", "").strip()
        try:
            val_float = float(cleaned)
            # 정수로 저장 (반올림)
            congestion_level = int(round(val_float))
        except ValueError:
            # 숫자로 변환 불가하면 스킵
            continue

        cursor.execute("""
            SELECT id FROM Congestion
            WHERE station_id=? AND day_type=? AND direction=? AND time_slot=?
        """, (station_id, day_type, direction, time_slot))
        exists = cursor.fetchone()
        if exists is None:
            try:
                cursor.execute("""
                    INSERT INTO Congestion (station_id, day_type, direction, time_slot, congestion_level)
                    VALUES (?, ?, ?, ?, ?)
                """, (station_id, day_type, direction, time_slot, congestion_level))
                congestion_insert_count += 1
            except sqlite3.IntegrityError:
                pass

        # 배치 커밋 (Congestion)
        if congestion_insert_count > 0 and congestion_insert_count % CONGESTION_BATCH == 0:
            conn.commit()
            print(f"중간 커밋(Congestion): 총 {congestion_insert_count}개 혼잡도 레코드 저장함")

# 루프 종료 후 최종 커밋
conn.commit()
print("모든 INSERT 커밋 완료됨.")


# 5) 결과 출력
cursor.execute("SELECT COUNT(*) FROM Station")
total_station = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM Congestion")
total_congestion = cursor.fetchone()[0]

print(f"CSV 전체 읽은 행 수: {row_count}")
print(f"이번 실행에서 신규 추가된 Station 수: {station_new_count}")
print(f"Station 테이블 총 레코드 수: {total_station}")
print(f"이번 실행에서 추가된 Congestion 레코드 수: {congestion_insert_count}")
print(f"Congestion 테이블 총 레코드 수: {total_congestion}")

# 정리
csv_file.close()
conn.close()
print("CSV 파일 및 DB 연결 종료")
