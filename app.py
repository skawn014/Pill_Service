"""
app.py  ─  Pill_Service 백엔드 메인 서버
──────────────────────────────────────────
실행:  python app.py
포트:  5000

YOLOv8 클래스 매핑 (data.yaml 기준)
  0: K-027567   1: K-030512   2: K-041140   3: K-043800
  4: 게보린정    5: 둘코락스   6: 렉스펜정   7: 로스토정
  8: 슬리펠정   9: 씬지록신정  10: 알러비정  11: 캐롤에프정

DB 에는 실제로 인식 가능한 이름 약 8종만 저장
  (코드명 0~3번은 학습은 됐지만 서비스에서는 제외)
"""

from flask import Flask, request, jsonify
from ultralytics import YOLO
import sqlite3, os, tempfile, hashlib

app = Flask(__name__)

# ── 경로 ──────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = os.path.join(BASE_DIR, "pills.db")
PT_PATH  = os.path.join(BASE_DIR, "best.pt")

# ── YOLO 클래스 ID → 알약 이름 매핑 (data.yaml 그대로) ───
YOLO_CLASS_NAMES = {
    0: "K-027567",
    1: "K-030512",
    2: "K-041140",
    3: "K-043800",
    4: "게보린정",
    5: "둘코락스",
    6: "렉스펜정",
    7: "로스토정",
    8: "슬리펠정",
    9: "씬지록신정",
    10: "알러비정",
    11: "캐롤에프정",
}

# ── 모델 로드 (서버 시작 시 1회) ──────────────────────────
model = YOLO(PT_PATH)
print(f"✅ YOLOv8 모델 로드 완료: {PT_PATH}")


# ── DB 유틸 ────────────────────────────────────────────────
def get_db():
    return sqlite3.connect(DB_PATH)


def init_db():
    """서버 시작 시 테이블 초기화"""
    conn = get_db()
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id TEXT PRIMARY KEY,
        password TEXT NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS inquiries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        category TEXT,
        title TEXT,
        content TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    conn.close()

init_db()


def find_pill_by_name(pill_name: str):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT pills_number, pills_name FROM pills_data "
            "WHERE pills_name LIKE ?",
            (f"%{pill_name.strip()}%",)
        )
        row = cur.fetchone()
        return (str(row[0]), row[1]) if row else (None, None)
    finally:
        conn.close()


# ── 회원가입 ───────────────────────────────────────────────
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    user_id = data.get("user_id", "").strip()
    password = data.get("password", "").strip()

    if not user_id or not password:
        return jsonify({"success": False, "message": "아이디/비밀번호를 입력하세요."}), 400

    pw_hash = hashlib.sha256(password.encode()).hexdigest()

    conn = get_db()
    try:
        conn.execute("INSERT INTO users (user_id, password) VALUES (?, ?)", (user_id, pw_hash))
        conn.commit()
        return jsonify({"success": True, "message": "회원가입 완료!"})
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "이미 존재하는 아이디입니다."}), 409
    finally:
        conn.close()


# ── 아이디 중복 확인 ───────────────────────────────────────
@app.route("/check_id", methods=["POST"])
def check_id():
    data = request.get_json()
    user_id = data.get("user_id", "").strip()

    if not user_id:
        return jsonify({"success": False, "message": "아이디를 입력하세요."}), 400

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        row = cur.fetchone()
        if row:
            return jsonify({"success": False, "message": "이미 사용 중인 아이디예요."})
        else:
            return jsonify({"success": True, "message": "사용 가능한 아이디예요! ✅"})
    finally:
        conn.close()


# ── 로그인 ─────────────────────────────────────────────────
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    user_id = data.get("user_id", "").strip()
    password = data.get("password", "").strip()

    if not user_id or not password:
        return jsonify({"success": False, "message": "아이디/비밀번호를 입력하세요."}), 400

    pw_hash = hashlib.sha256(password.encode()).hexdigest()

    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM users WHERE user_id=? AND password=?", (user_id, pw_hash))
        row = cur.fetchone()
        if row:
            return jsonify({"success": True, "message": "로그인 성공!"})
        else:
            return jsonify({"success": False, "message": "아이디 또는 비밀번호가 틀렸어요."}), 401
    finally:
        conn.close()


# ── 고객센터 문의 ──────────────────────────────────────────
@app.route("/inquiry", methods=["POST"])
def inquiry():
    data = request.get_json()
    user_id = data.get("user_id", "익명")
    category = data.get("category", "")
    title = data.get("title", "")
    content = data.get("content", "")

    if not title or not content:
        return jsonify({"success": False, "message": "제목과 내용을 입력하세요."}), 400

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO inquiries (user_id, category, title, content) VALUES (?, ?, ?, ?)",
            (user_id, category, title, content)
        )
        conn.commit()
        return jsonify({"success": True, "message": "문의가 접수됐어요!"})
    finally:
        conn.close()


# ── 메인 API: 알약 검증 ────────────────────────────────────
@app.route("/verify_pill", methods=["POST"])
def verify_pill():
    if "pill_name" not in request.form:
        return jsonify({"error": "pill_name 이 없습니다."}), 400
    if "image" not in request.files:
        return jsonify({"error": "image 파일이 없습니다."}), 400

    pill_name  = request.form["pill_name"].strip()
    image_file = request.files["image"]

    db_number, db_name = find_pill_by_name(pill_name)
    if db_number is None:
        return jsonify({
            "match"           : False,
            "input_pill_name" : pill_name,
            "detected_name"   : None,
            "confidence"      : None,
            "message"         : f"'{pill_name}'은 등록된 약이 아닙니다."
        }), 404

    suffix = os.path.splitext(image_file.filename or ".jpg")[-1] or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        image_file.save(tmp.name)
        tmp_path = tmp.name

    try:
        results = model(tmp_path, verbose=False)
    finally:
        os.remove(tmp_path)

    detected_name = None
    confidence    = None

    if results and len(results[0].boxes) > 0:
        boxes     = results[0].boxes
        best_idx  = int(boxes.conf.argmax())
        confidence = float(boxes.conf[best_idx])
        class_id  = int(boxes.cls[best_idx])
        detected_name = YOLO_CLASS_NAMES.get(class_id, f"class_{class_id}")

    match = (
        detected_name is not None
        and db_name.strip() == detected_name.strip()
    )

    if detected_name is None:
        message = "이미지에서 알약을 감지하지 못했습니다. 밝은 곳에서 다시 촬영해주세요."
    elif match:
        pct = round(confidence * 100, 1)
        message = f"✅ 일치 ({pct}%): '{pill_name}' 맞습니다!"
    else:
        message = f"❌ 불일치: 입력한 약은 '{pill_name}'이지만 촬영된 약은 '{detected_name}'입니다."

    return jsonify({
        "match"           : match,
        "input_pill_name" : pill_name,
        "detected_name"   : detected_name,
        "confidence"      : round(confidence, 4) if confidence is not None else None,
        "message"         : message
    })


# ── 알약 검색 API ──────────────────────────────────────────
@app.route("/pills/search", methods=["GET"])
def search_pills():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "검색어 q 를 입력하세요."}), 400

    conn = get_db()
    cur  = conn.cursor()
    cur.execute(
        "SELECT pills_number, pills_name FROM pills_data WHERE pills_name LIKE ? LIMIT 20",
        (f"%{q}%",)
    )
    rows = cur.fetchall()
    conn.close()

    return jsonify({
        "query"  : q,
        "count"  : len(rows),
        "results": [{"pills_number": r[0], "pills_name": r[1]} for r in rows]
    })


# ── 헬스체크 ───────────────────────────────────────────────
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "classes": len(YOLO_CLASS_NAMES)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)