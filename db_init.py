"""
db_init.py  ─  pills.db 초기 세팅
──────────────────────────────────
실행:  python db_init.py
결과:  같은 폴더에 pills.db 생성 + 데이터 12건 삽입

data.yaml 기준 클래스 12개 중
실제로 이름이 있는 8종만 DB에 저장.
(K-027567 등 코드명 4종은 UI에서 선택 불가)
"""

import sqlite3, os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "pills.db")

PILLS = [
    # (pills_number, pills_name)  ← YOLO class_id 를 번호로 사용
    ("4",  "게보린정"),
    ("5",  "둘코락스"),
    ("6",  "렉스펜정"),
    ("7",  "로스토정"),
    ("8",  "슬리펠정"),
    ("9",  "씬지록신정"),
    ("10", "알러비정"),
    ("11", "캐롤에프정"),
]


def init():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()

    # pills_data 테이블 생성 (없으면)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pills_data (
            pills_number TEXT PRIMARY KEY,
            pills_name   TEXT NOT NULL
        )
    """)

    # 데이터 삽입 (중복 무시)
    cur.executemany(
        "INSERT OR IGNORE INTO pills_data (pills_number, pills_name) VALUES (?, ?)",
        PILLS
    )

    conn.commit()

    # 확인 출력
    cur.execute("SELECT * FROM pills_data ORDER BY CAST(pills_number AS INTEGER)")
    rows = cur.fetchall()
    conn.close()

    print(f"✅ pills.db 초기화 완료 → {DB_PATH}")
    print(f"{'번호':<8} {'약 이름'}")
    print("-" * 24)
    for r in rows:
        print(f"{r[0]:<8} {r[1]}")


if __name__ == "__main__":
    init()
