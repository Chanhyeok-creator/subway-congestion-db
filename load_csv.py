import sqlite3
import csv

DB_PATH = "database.db"
CSV_PATH = "서울교통공사_지하철혼잡도정보_20250630.csv"

# 1. 데이터베이스 연결
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

print("데이터베이스 연결 완료됨")

# 2. 역 정보를 저장할 테이블 생성
cursor.execute("""
CREATE TABLE IF NOT EXISTS Station (
    station_id INTEGER PRIMARY KEY AUTOINCREMENT,
    line INTEGER,
    station_number TEXT,
    station_name TEXT
)
""")

print("Station 테이블 생성 완료됨")

# 3. 혼잡도 정보를 저장할 테이블 생성함
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

# 4. 변경사항 저장
conn.commit()

# 5. 데이터베이스 연결 종료
conn.close()

print("데이터베이스 설정 완료됨")

#csv파일 열고 첫 줄을 확인해보자
csv_file = open("서울교통공사_지하철혼잡도정보_20250630.csv", encoding="cp949") #이게 utf-8이 아니라 cp949였네
csv_reader = csv.reader(csv_file)

header = next(csv_reader)
print("CSV 헤더:")
print(header)

# 데이터 한 줄만 출력
first_row = next(csv_reader)
print("첫 번째 데이터 행은?:")
print(first_row)

csv_file.close()