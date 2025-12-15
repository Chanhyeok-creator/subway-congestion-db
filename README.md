# Subway Congestion Database Web App

서울 지하철의 혼잡도 정보를 웹에서 조회하고 관리할 수 있는  
Flask + SQLite 기반 데이터베이스 웹 응용 프로젝트입니다.

---

## 📌 프로젝트 목적
서울을 여행하는 지방 사람들 또는  
덜 붐비는 지하철을 이용하고 싶은 사용자에게  
지하철 혼잡도 정보를 제공하기 위해 제작되었습니다.

CSV 형태의 공개 데이터를 데이터베이스로 구조화하고,  
웹 UI를 통해 조회 및 관리(CRUD)할 수 있도록 구현했습니다.

---

## 🗂 데이터 출처
- 서울교통공사 지하철 혼잡도 정보 (공공데이터)
- https://www.data.go.kr/data/15071311/fileData.do

---

## 🛠 개발 환경
- Language: Python
- Web Framework: Flask
- Database: SQLite
- Frontend: HTML (Jinja2 Template)

---

## 🧩 데이터베이스 구성

### Station 테이블
- 호선, 역번호, 역이름 정보 저장
- 중복 방지를 위해 (호선, 역번호) UNIQUE 처리

### Congestion 테이블
- 역별 / 요일별 / 방향별 / 시간대별 혼잡도 저장
- 혼잡도 값은 NULL 허용 (데이터 없음)
- Station과 1:N 관계 (외래키 + CASCADE 삭제)

※ 방향은 CSV의 내선/외선을  
→ 내부적으로 상선/하선으로 정규화하여 저장합니다.

---

## ⚙ 주요 기능
- CSV 파일을 읽어 DB에 데이터 저장
- 혼잡도 조회 (역 / 요일 / 방향 / 시간대 선택)
- 역 정보 추가 / 수정 / 삭제
- 혼잡도 데이터 추가 / 수정 / 삭제
- 혼잡도 값이 없을 경우 "데이터 없음" 표시
- 원본 CSV 상태로 데이터베이스 초기화 기능 제공

---

## ▶ 실행 방법
```bash
pip install flask
python3 app.py
