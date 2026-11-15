from flask import Flask, render_template, request, redirect, url_for, session, flash, g, abort, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from pathlib import Path
from datetime import datetime
from function.randomroom import allocate_rooms_logic,prepare_allocation, save_allocation, get_room_numbers, add_room, rename_room, delete_room, reset_room_allocation, swap_student_rooms, get_room_exclusions, add_room_exclusion, delete_room_exclusion, clear_room_exclusions, get_grade
import sqlite3
import secrets
import hmac
import re
import sys
import time
import threading
import os


BASE_DIR = Path(__file__).resolve().parent.parent   
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR = TEMPLATE_DIR / "static"
DB_PATH = BASE_DIR / "database.db"
SECRET_PATH = BASE_DIR / ".flask_secret"

if not SECRET_PATH.exists():
    SECRET_PATH.write_text(
        secrets.token_hex(32),
        encoding="utf-8"
    )

app = Flask(
    __name__,
    template_folder=str(TEMPLATE_DIR),
    static_folder=str(STATIC_DIR)
)

app.secret_key = SECRET_PATH.read_text(
    encoding="utf-8"
).strip()

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax"
)



def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row

    return g.db


@app.teardown_appcontext
def close_db(error):
    db = g.pop("db", None)

    if db is not None:
        db.close()


def init_db():
    with app.app_context():
        db = get_db()

        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                gender TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'student'
                    CHECK (role IN ('student', 'admin')),
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            )
        """)

        db.commit()


init_db()


def init_student_columns():
    with app.app_context():
        db = get_db()

        columns = [row["name"] for row in db.execute("PRAGMA table_info(users)")]

        new_columns = {"gender": "TEXT", "room_number": "TEXT"}

        for column_name, column_type in new_columns.items():
            if column_name not in columns:
                db.execute(
                    f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"
                )

        db.commit()


init_student_columns()


def init_points_db():
    with app.app_context():
        db = get_db()

        db.execute("""
            CREATE TABLE IF NOT EXISTS points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                point_type TEXT NOT NULL
                    CHECK (point_type IN ('reward', 'penalty')),
                amount INTEGER NOT NULL CHECK (amount > 0),
                reason TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (student_id)
                    REFERENCES users(id)
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS appeals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                point_id INTEGER NOT NULL UNIQUE,
                student_id INTEGER NOT NULL,
                reason TEXT NOT NULL,

                status TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN (
                        'pending', 'approved', 'rejected'
                    )),

                admin_comment TEXT,
                reviewer_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TEXT,

                FOREIGN KEY (point_id)
                    REFERENCES points(id),

                FOREIGN KEY (student_id)
                    REFERENCES users(id)
            )
        """)

        db.commit()


init_points_db()



def current_user():
    user_id = session.get("user_id")

    if user_id is None:
        return None

    db = get_db()

    return db.execute(
        "SELECT * FROM users WHERE id = ? AND active = 1",
        (user_id,)
    ).fetchone()


def login_required(role=None):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            user = current_user()

            if user is None:
                session.clear()
                return redirect(url_for("login"))

            if role and user["role"] != role:
                abort(403)

            return func(*args, **kwargs)

        return wrapper
    return decorator




@app.before_request
def check_csrf():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(32)

    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        submitted = (
            request.headers.get("X-CSRF-Token")
            or request.form.get("csrf_token", "")
        )

        if not hmac.compare_digest(
            session["_csrf"], submitted
        ):
            abort(400)


@app.context_processor
def inject_csrf():
    return {"csrf_token": session.get("_csrf", "")}



@app.route("/")
def home():
    user = current_user()

    if user is None:
        return redirect(url_for("login"))

    if user["role"] == "admin":
        return redirect(url_for("admin"))

    return redirect(url_for("students"))



@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":
        return render_template(
            "login.html", mode="register"
        )

    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    gender = request.form.get("gender", "").strip()

    if gender not in ("남", "여"):
        flash("성별을 선택해 주세요.")
        return redirect(url_for("register"))

    if not re.fullmatch(r"[123][0-9]{3}", username):
        flash("학번은 1~3으로 시작하는 4자리 숫자여야 합니다.")
        return redirect(url_for("register"))

    if len(password) < 8:
        flash("비밀번호는 8자 이상이어야 합니다.")
        return redirect(url_for("register"))

    db = get_db()

    existing = db.execute(
        "SELECT id FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    if existing:
        flash("이미 존재하는 아이디입니다.")
        return redirect(url_for("register"))

    password_hash = generate_password_hash(password)

    db.execute(
        """
        INSERT INTO users
        (username, password_hash, role, gender)
        VALUES (?, ?, 'student', ?)
        """,
        (username, password_hash, gender)
)

    db.commit()

    flash("회원가입이 완료되었습니다. 로그인하세요.")
    return redirect(url_for("login"))




@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "GET":
        return render_template(
            "login.html", mode="login"
        )

    username = request.form.get(
        "username", ""
    ).strip()

    password = request.form.get(
        "password", ""
    )

    db = get_db()

    user = db.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    if (
        user is None
        or not user["active"]
        or not check_password_hash(
            user["password_hash"], password
        )
    ):
        flash("아이디 또는 비밀번호가 올바르지 않습니다.")
        return redirect(url_for("login"))

    session.clear()
    session["user_id"] = user["id"]
    session["_csrf"] = secrets.token_urlsafe(32)

    return redirect(url_for("home"))



@app.route("/logout", methods=["POST"])
@login_required()
def logout():
    session.clear()
    return redirect(url_for("login"))



@app.route("/students")
@login_required("student")
def students():
    user = current_user()
    db = get_db()

    student = db.execute(
        "SELECT room_number FROM users WHERE id = ?",
        (user["id"],)
    ).fetchone()

    room_number = student["room_number"] if student else None

    return render_template(
        "students.html",
        username=user["username"],
        room_number=room_number
    )



@app.route("/admin")
@login_required("admin")
def admin():
    db = get_db()

    users = db.execute(
        """
        SELECT id, username, role, active, created_at
        FROM users
        ORDER BY id DESC
        """
    ).fetchall()

    return render_template(
        "admin.html",
        users=users
    )




@app.route(
    "/admin/users/<int:user_id>/toggle",
    methods=["POST"]
)
@login_required("admin")
def toggle_user(user_id):
    db = get_db()

    user = db.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()

    if user is None:
        abort(404)

    if user["role"] != "student":
        abort(403)

    new_status = 0 if user["active"] else 1

    db.execute(
        "UPDATE users SET active = ? WHERE id = ?",
        (new_status, user_id)
    )

    db.commit()

    flash("계정 상태를 변경했습니다.")
    return redirect(url_for("admin"))



def create_admin():
    username = input("관리자 아이디: ").strip()
    gender = input("관리자 성별 (남/여): ").strip()
    password = input("관리자 비밀번호: ").strip()

    if not re.fullmatch(r"[A-Za-z0-9_]{3,20}", username):
        print("아이디 형식이 올바르지 않습니다.")
        return

    if gender not in ("남", "여", "남자", "여자"):
        print("성별은 '남' 또는 '여'로 입력해야 합니다.")
        return

    if len(password) < 8:
        print("비밀번호는 8자 이상이어야 합니다.")
        return

    with app.app_context():
        db = get_db()

        try:
            db.execute(
                """
                INSERT INTO users
                (username, gender, password_hash, role)
                VALUES (?, ?, ?, 'admin')
                """,
                (
                    username,
                    gender,
                    generate_password_hash(password)
                )
            )

            db.commit()
            print("관리자 계정 생성 완료")

        except sqlite3.IntegrityError:
            print("이미 사용 중인 아이디입니다.")



@app.route("/api/csrf", methods=["GET"])
@login_required()
def api_csrf():
    return jsonify({
        "csrf_token": session["_csrf"]
    })



@app.route("/api/points", methods=["GET"])
@login_required("student")
def get_points():
    user = current_user()
    db = get_db()

    rows = db.execute("""
        SELECT id, point_type, amount,
               reason, created_at
        FROM points
        WHERE student_id = ?
        ORDER BY id DESC
    """, (user["id"],)).fetchall()

    return jsonify({
        "success": True,
        "points": [dict(row) for row in rows]
    })



@app.route("/api/appeals", methods=["POST"])
@login_required("student")
def create_appeal():
    user = current_user()
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "message": "올바른 JSON 데이터를 보내세요."
        }), 400

    point_id = data.get("point_id")
    reason = data.get("reason")

    if type(point_id) is not int or point_id < 1:
        return jsonify({
            "success": False,
            "message": "올바른 상벌점 번호를 선택하세요."
        }), 400

    if not isinstance(reason, str) or not reason.strip():
        return jsonify({
            "success": False,
            "message": "이의제기 사유를 작성하세요."
        }), 400

    reason = reason.strip()

    if len(reason) > 2000:
        return jsonify({
            "success": False,
            "message": "사유는 2000자 이하로 작성하세요."
        }), 400

    db = get_db()

    
    point = db.execute("""
        SELECT id FROM points
        WHERE id = ? AND student_id = ?
    """, (point_id, user["id"])).fetchone()

    if point is None:
        return jsonify({
            "success": False,
            "message": "신청 가능한 상벌점 기록이 없습니다."
        }), 404

    
    try:
        cursor = db.execute("""
            INSERT INTO appeals
            (point_id, student_id, reason)
            VALUES (?, ?, ?)
        """, (
            point_id,
            user["id"],
            reason
        ))

        db.commit()

    except sqlite3.IntegrityError:
        db.rollback()
        return jsonify({
            "success": False,
            "message": "이미 이의제기를 신청한 기록입니다."
        }), 409

    return jsonify({
        "success": True,
        "message": "이의제기가 접수되었습니다.",
        "appeal_id": cursor.lastrowid
    }), 201



@app.route("/api/appeals", methods=["GET"])
@login_required("student")
def get_appeals():
    user = current_user()
    db = get_db()

    rows = db.execute("""
        SELECT
            a.id,
            a.point_id,
            a.reason,
            a.status,
            a.admin_comment,
            a.created_at,
            a.reviewed_at,
            p.point_type,
            p.amount
        FROM appeals a
        JOIN points p ON a.point_id = p.id
        WHERE a.student_id = ?
        ORDER BY a.id DESC
    """, (user["id"],)).fetchall()

    return jsonify({
        "success": True,
        "appeals": [dict(row) for row in rows]
    })




@app.route("/api/admin/points", methods=["GET"])
@login_required("admin")
def admin_get_points():
    db = get_db()

    rows = db.execute("""
        SELECT
            p.id,
            p.student_id,
            p.point_type,
            p.amount,
            p.reason,
            p.created_at,
            u.username
        FROM points p
        JOIN users u ON p.student_id = u.id
        ORDER BY p.id DESC
    """).fetchall()

    return jsonify({
        "success": True,
        "points": [dict(row) for row in rows]
    })


@app.route("/api/admin/points", methods=["POST"])
@login_required("admin")
def create_point():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "message": "올바른 데이터를 입력하세요."
        }), 400

    username = data.get("username")
    point_type = data.get("point_type")
    amount = data.get("amount")
    reason = data.get("reason")

    if not isinstance(username, str) or not username.strip():
        return jsonify({
            "success": False,
            "message": "학생 아이디를 입력하세요."
        }), 400

    if point_type not in ("reward", "penalty"):
        return jsonify({
            "success": False,
            "message": "상점 또는 벌점을 선택하세요."
        }), 400

    if type(amount) is not int or not 1 <= amount <= 100:
        return jsonify({
            "success": False,
            "message": "점수는 1~100 사이의 정수여야 합니다."
        }), 400

    if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 500:
        return jsonify({
            "success": False,
            "message": "사유를 1~500자로 입력하세요."
        }), 400

    db = get_db()

    
    student = db.execute("""
        SELECT id
        FROM users
        WHERE username = ?
          AND role = 'student'
          AND active = 1
    """, (username.strip(),)).fetchone()

    if student is None:
        return jsonify({
            "success": False,
            "message": "해당 아이디의 학생을 찾을 수 없습니다."
        }), 404

    
    cursor = db.execute("""
        INSERT INTO points
        (student_id, point_type, amount, reason)
        VALUES (?, ?, ?, ?)
    """, (
        student["id"],
        point_type,
        amount,
        reason.strip()
    ))

    db.commit()

    return jsonify({
        "success": True,
        "message": "상벌점이 등록되었습니다.",
        "point_id": cursor.lastrowid
    }), 201




@app.route("/api/admin/points/ranking", methods=["GET"])
@login_required("admin")
def get_points_ranking():
    db = get_db()

    rows = db.execute("""
        SELECT
            u.username,
            SUM(p.amount) AS total_reward
        FROM points p
        JOIN users u ON p.student_id = u.id
        WHERE p.point_type = 'reward'
          AND u.role = 'student'
          AND p.created_at >= datetime('now', '-30 days')
        GROUP BY u.id, u.username
        ORDER BY total_reward DESC, u.username ASC
    """).fetchall()

    if not rows:
        return jsonify({
            "success": True,
            "period": "last_30_days",
            "top_reward": 0,
            "winners": []
        })

    top_reward = rows[0]["total_reward"]

    winners = [
        {
            "username": row["username"],
            "total_reward": row["total_reward"]
        }
        for row in rows
        if row["total_reward"] == top_reward
    ]

    return jsonify({
        "success": True,
        "period": "last_30_days",
        "top_reward": top_reward,
        "winners": winners
    })



@app.route("/api/admin/points/student", methods=["GET"])
@login_required("admin")
def get_student_points():
    username = request.args.get(
        "username", ""
    ).strip()

    if not username:
        return jsonify({
            "success": False,
            "message": "학생 아이디를 입력하세요."
        }), 400

    db = get_db()

    student = db.execute("""
        SELECT id, username
        FROM users
        WHERE username = ?
          AND role = 'student'
    """, (username,)).fetchone()

    if student is None:
        return jsonify({
            "success": False,
            "message": "해당 학생을 찾을 수 없습니다."
        }), 404

    rows = db.execute("""
        SELECT
            id,
            point_type,
            amount,
            reason,
            created_at
        FROM points
        WHERE student_id = ?
        ORDER BY created_at DESC, id DESC
    """, (student["id"],)).fetchall()

    points = [dict(row) for row in rows]

    total_reward = sum(
        p["amount"] for p in points
        if p["point_type"] == "reward"
    )

    total_penalty = sum(
        p["amount"] for p in points
        if p["point_type"] == "penalty"
    )

    return jsonify({
        "success": True,
        "username": student["username"],
        "total_reward": total_reward,
        "total_penalty": total_penalty,
        "total_points": total_reward - total_penalty,
        "points": points
    })



@app.route("/api/admin/appeals", methods=["GET"])
@login_required("admin")
def admin_get_appeals():
    db = get_db()

    rows = db.execute("""
        SELECT
            a.id,
            a.point_id,
            a.reason,
            a.status,
            a.admin_comment,
            a.created_at,
            a.reviewed_at,
            u.username,
            p.point_type,
            p.amount,
            p.reason AS point_reason
        FROM appeals a
        JOIN users u ON a.student_id = u.id
        JOIN points p ON a.point_id = p.id
        ORDER BY a.id DESC
    """).fetchall()

    return jsonify({
        "success": True,
        "appeals": [dict(row) for row in rows]
    })



@app.route(
    "/api/admin/appeals/<int:appeal_id>/review",
    methods=["POST"]
)
@login_required("admin")
def review_appeal(appeal_id):
    admin_user = current_user()
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "message": "올바른 JSON 데이터가 필요합니다."
        }), 400

    status = data.get("status")
    comment = data.get("admin_comment")

    if status not in ("approved", "rejected"):
        return jsonify({
            "success": False,
            "message": "처리 상태가 올바르지 않습니다."
        }), 400

    if not isinstance(comment, str) or not 1 <= len(comment.strip()) <= 1000:
        return jsonify({
            "success": False,
            "message": "관리자 의견을 1~1000자로 입력하세요."
        }), 400

    db = get_db()

    cursor = db.execute("""
        UPDATE appeals
        SET
            status = ?,
            admin_comment = ?,
            reviewer_id = ?,
            reviewed_at = CURRENT_TIMESTAMP
        WHERE id = ? AND status = 'pending'
    """, (
        status,
        comment.strip(),
        admin_user["id"],
        appeal_id
    ))

    if cursor.rowcount == 0:
        return jsonify({
            "success": False,
            "message": "대기 중인 이의제기를 찾을 수 없습니다."
        }), 409

    db.commit()

    return jsonify({
        "success": True,
        "message": "심사가 완료되었습니다."
    })



def init_repairs_db():
    with app.app_context():
        db = get_db()

        db.execute("""
            CREATE TABLE IF NOT EXISTS repairs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER NOT NULL,
                room TEXT NOT NULL,
                student_number TEXT NOT NULL,
                student_name TEXT NOT NULL,
                description TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed')),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TEXT,
                completed_by INTEGER,
                FOREIGN KEY (student_id) REFERENCES users(id),
                FOREIGN KEY (completed_by) REFERENCES users(id)
            )
        """)

        db.commit()


init_repairs_db()



@app.route("/api/repairs", methods=["POST"])
@login_required("student")
def create_repair():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"success": False, "message": "올바른 데이터를 입력하세요."}), 400

    fields = {
        "room": ("호실", 30),
        "student_number": ("학번", 20),
        "name": ("이름", 40),
        "description": ("고장 내용", 2000)
    }

    values = {}

    for key, (label, maximum) in fields.items():
        value = data.get(key)

        if not isinstance(value, str) or not 1 <= len(value.strip()) <= maximum:
            return jsonify({
                "success": False,
                "message": f"{label}을(를) 1~{maximum}자로 입력하세요."
            }), 400

        values[key] = value.strip()

    db = get_db()
    user = current_user()

    cursor = db.execute("""
        INSERT INTO repairs (student_id, room, student_number, student_name, description)
        VALUES (?, ?, ?, ?, ?)
    """, (
        user["id"],
        values["room"],
        values["student_number"],
        values["name"],
        values["description"]
    ))

    db.commit()

    return jsonify({
        "success": True,
        "message": "수리 요청이 접수되었습니다.",
        "repair_id": cursor.lastrowid
    }), 201



@app.route("/api/repairs", methods=["GET"])
@login_required("student")
def get_repairs():
    db = get_db()

    rows = db.execute("""
        SELECT id, room, student_number, student_name AS name,
               description, status, created_at, completed_at
        FROM repairs
        WHERE student_id = ?
        ORDER BY id DESC
    """, (current_user()["id"],)).fetchall()

    return jsonify({
        "success": True,
        "repairs": [dict(row) for row in rows]
    })



@app.route("/api/admin/repairs", methods=["GET"])
@login_required("admin")
def admin_get_repairs():
    db = get_db()

    rows = db.execute("""
        SELECT r.id, r.room, r.student_number, r.student_name AS name,
               r.description, r.status, r.created_at, u.username
        FROM repairs r
        JOIN users u ON u.id = r.student_id
        WHERE r.status = 'pending'
        ORDER BY r.id ASC
    """).fetchall()

    return jsonify({
        "success": True,
        "repairs": [dict(row) for row in rows]
    })



@app.route("/api/admin/repairs/<int:repair_id>/complete", methods=["POST"])
@login_required("admin")
def complete_repair(repair_id):
    db = get_db()

    cursor = db.execute("""
        UPDATE repairs
        SET status = 'completed',
            completed_at = CURRENT_TIMESTAMP,
            completed_by = ?
        WHERE id = ? AND status = 'pending'
    """, (current_user()["id"], repair_id))

    if cursor.rowcount == 0:
        return jsonify({
            "success": False,
            "message": "대기 중인 수리 요청을 찾을 수 없습니다."
        }), 404

    db.commit()

    return jsonify({
        "success": True,
        "message": "수리 완료 처리되었습니다."
    })




@app.route("/api/admin/rooms/allocate", methods=["POST"])
@login_required("admin")
def admin_allocate_rooms():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "success": False,
            "message": "학년과 성별을 선택해 주세요."
        }), 400

    grade = data.get("grade")
    gender = data.get("gender")

    if type(grade) is not int or grade not in (1, 2, 3):
        return jsonify({
            "success": False,
            "message": "학년은 1~3학년 중 선택해 주세요."
        }), 400

    if gender not in ("남", "여"):
        return jsonify({
            "success": False,
            "message": "성별은 남 또는 여 중 선택해 주세요."
        }), 400

    result = allocate_rooms_logic(grade, gender)

    if result["status"] == "success":
        return jsonify({
            "success": True,
            "message": result["message"],
            "rooms": result.get("data", [])
        })

    return jsonify({
        "success": False,
        "message": result["message"]
    }), 400



@app.route("/api/admin/rooms/prepare", methods=["POST"])
@login_required("admin")
def admin_prepare_rooms():

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "학년과 성별을 선택해 주세요."
        }), 400

    grade = data.get("grade")
    gender = data.get("gender")

    if type(grade) is not int or grade not in (1, 2, 3):
        return jsonify({
            "status": "error",
            "message": "학년은 1~3학년 중 선택해 주세요."
        }), 400

    if gender not in ("남", "여"):
        return jsonify({
            "status": "error",
            "message": "성별은 남 또는 여 중 선택해 주세요."
        }), 400

    result = prepare_allocation(grade, gender)

    if result["status"] == "success":
        session["pending_room_allocation"] = {
            "assignments": result["data"],
            "grade": grade,
            "gender": gender
        }
        return jsonify(result)

    session.pop("pending_room_allocation", None)

    return jsonify(result), 400



@app.route("/api/admin/rooms/save", methods=["POST"])
@login_required("admin")
def admin_save_rooms():

    pending = session.get("pending_room_allocation")

    if not isinstance(pending, dict):
        return jsonify({
            "status": "error",
            "message": "저장할 방 배정 결과가 없습니다."
        }), 400

    assignments = pending.get("assignments")
    grade = pending.get("grade")
    gender = pending.get("gender")

    if (
        not isinstance(assignments, list)
        or type(grade) is not int
        or grade not in (1, 2, 3)
        or gender not in ("남", "여")
    ):
        session.pop("pending_room_allocation", None)
        return jsonify({
            "status": "error",
            "message": "방 배정 정보가 올바르지 않습니다."
        }), 400

    result = save_allocation(assignments, grade, gender)

    if result["status"] == "success":
        session.pop("pending_room_allocation", None)
        return jsonify(result)

    return jsonify(result), 400



@app.route("/api/admin/rooms", methods=["GET"])
@login_required("admin")
def admin_get_rooms():
    room_numbers = get_room_numbers()
    db = get_db()

    rows = db.execute("""
        SELECT id, username, gender, room_number
        FROM users
        WHERE role = 'student'
          AND active = 1
          AND room_number IS NOT NULL
        ORDER BY id
    """).fetchall()

    rooms = [
        {
            "room_number": room,
            "capacity": 4,
            "assigned_count": 0,
            "occupants": [],
            "students": []
        }
        for room in room_numbers
    ]

    room_map = {
        room["room_number"]: room
        for room in rooms
    }

    for row in rows:
        room_number = str(row["room_number"])

        if room_number not in room_map:
            continue

        room = room_map[room_number]
        username = row["username"]
        grade = get_grade(username)

        room["occupants"].append({
            "student_id": row["id"],
            "username": username
        })

        room["students"].append({
            "id": row["id"],
            "username": username,
            "grade": grade,
            "gender": row["gender"]
        })

        room["assigned_count"] += 1

    return jsonify({
        "success": True,
        "status": "success",
        "rooms": rooms,
        "data": rooms
    })



def room_api_response(result, success_code=200):
    """randomroom.py의 결과를 HTTP 응답으로 변환"""
    if result["status"] == "success":
        return jsonify(result), success_code

    message = result.get("message", "요청 처리에 실패했습니다.")

    if (
        "이미 존재" in message
        or "이미 등록" in message
        or "배정된 학생이 있는 방" in message
        or "교환할 수 없습니다" in message
    ):
        code = 409
    elif "존재하지 않" in message or "해당 방이 존재하지" in message:
        code = 404
    else:
        code = 400

    return jsonify(result), code


def invalidate_pending_rooms():
    """현재 관리자 세션의 미저장 추첨 결과 폐기"""
    session.pop("pending_room_allocation", None)



@app.route("/api/admin/rooms", methods=["POST"])
@login_required("admin")
def admin_add_room():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "올바른 JSON 데이터를 보내세요."
        }), 400

    room_number = data.get("room_number")

    if not isinstance(room_number, str) or not room_number.strip():
        return jsonify({
            "status": "error",
            "message": "방 번호를 문자열로 입력해 주세요."
        }), 400

    result = add_room(room_number)

    if result["status"] == "success":
        invalidate_pending_rooms()

    return room_api_response(result, 201)


@app.route("/api/admin/rooms/<room_number>", methods=["PATCH"])
@login_required("admin")
def admin_rename_room(room_number):
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "올바른 JSON 데이터를 보내세요."
        }), 400

    new_number = data.get("new_room_number")

    if not isinstance(new_number, str) or not new_number.strip():
        return jsonify({
            "status": "error",
            "message": "새 방 번호를 입력해 주세요."
        }), 400

    result = rename_room(room_number, new_number)

    if result["status"] == "success":
        invalidate_pending_rooms()

    return room_api_response(result)


@app.route("/api/admin/rooms/<room_number>", methods=["DELETE"])
@login_required("admin")
def admin_delete_room(room_number):
    result = delete_room(room_number)

    if result["status"] == "success":
        invalidate_pending_rooms()

    return room_api_response(result)


@app.route("/api/admin/rooms/reset", methods=["POST"])
@login_required("admin")
def admin_reset_rooms():
    result = reset_room_allocation()

    if result["status"] == "success":
        invalidate_pending_rooms()

    return room_api_response(result)


@app.route("/api/admin/rooms/swap", methods=["POST"])
@login_required("admin")
def admin_swap_rooms():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "올바른 JSON 데이터를 보내세요."
        }), 400

    student_id_1 = data.get("student_id_1")
    student_id_2 = data.get("student_id_2")

    if (
        type(student_id_1) is not int
        or type(student_id_2) is not int
        or student_id_1 < 1
        or student_id_2 < 1
        or student_id_1 == student_id_2
    ):
        return jsonify({
            "status": "error",
            "message": "서로 다른 두 학생의 ID를 입력해 주세요."
        }), 400

    result = swap_student_rooms(student_id_1, student_id_2)

    if result["status"] == "success":
        invalidate_pending_rooms()

    return room_api_response(result)



@app.route("/api/admin/rooms/exclusions", methods=["GET"])
@login_required("admin")
def admin_get_room_exclusions():
    result = get_room_exclusions()
    return room_api_response(result)


@app.route("/api/admin/rooms/exclusions", methods=["POST"])
@login_required("admin")
def admin_add_room_exclusion():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "message": "올바른 JSON 데이터를 보내세요."
        }), 400

    student_id_1 = data.get("student_id_1")
    student_id_2 = data.get("student_id_2")

    if (
        type(student_id_1) is not int
        or type(student_id_2) is not int
        or student_id_1 < 1
        or student_id_2 < 1
        or student_id_1 == student_id_2
    ):
        return jsonify({
            "status": "error",
            "message": "서로 다른 두 학생의 ID를 입력해 주세요."
        }), 400


    result = add_room_exclusion(student_id_1, student_id_2)

    if result["status"] == "success":
        invalidate_pending_rooms()

    return room_api_response(result, 201)


@app.route(
    "/api/admin/rooms/exclusions/<int:exclusion_id>",
    methods=["DELETE"]
)
@login_required("admin")
def admin_delete_room_exclusion(exclusion_id):
    result = delete_room_exclusion(exclusion_id)

    if result["status"] == "success":
        invalidate_pending_rooms()

    return room_api_response(result)


@app.route(
    "/api/admin/rooms/exclusions/clear",
    methods=["DELETE"]
)
@login_required("admin")
def admin_clear_room_exclusions():

    result = clear_room_exclusions()

    if result["status"] == "success":
        session.pop("pending_room_allocation", None)

    return room_api_response(result)


@app.route("/api/admin/rooms/students", methods=["GET"])
@login_required("admin")
def admin_room_students():
    db = get_db()

    rows = db.execute("""
        SELECT id, username, gender, room_number
        FROM users
        WHERE role = 'student'
          AND active = 1
        ORDER BY username, id
    """).fetchall()

    students = []

    for row in rows:
        student = dict(row)
        student["grade"] = get_grade(student["username"])
        students.append(student)

    return jsonify({
        "status": "success",
        "data": students
    })



CAPTURE_DIR = BASE_DIR / "captures"
CAPTURE_DIR.mkdir(exist_ok=True)


def init_cctv_db():
    with app.app_context():
        db = get_db()

        db.execute("""
            CREATE TABLE IF NOT EXISTS cctv_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL UNIQUE,
                event_type TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                expires_at REAL NOT NULL
            )
        """)

        db.commit()


init_cctv_db()



def cleanup_expired_videos():
    now = time.time()

    with sqlite3.connect(DB_PATH, timeout=10) as db:
        db.row_factory = sqlite3.Row

        expired = db.execute("""
            SELECT id, filename
            FROM cctv_events
            WHERE expires_at <= ?
        """, (now,)).fetchall()

        for event in expired:
            filename = event["filename"]

            if Path(filename).name != filename:
                continue

            path = CAPTURE_DIR / filename

            try:
                path.unlink(missing_ok=True)
            except OSError as error:
                print("CCTV 영상 삭제 실패:", error)
                continue

            db.execute("""
                DELETE FROM cctv_events
                WHERE id = ?
            """, (event["id"],))

        db.commit()


def cctv_cleanup_worker():
    while True:
        try:
            cleanup_expired_videos()
        except Exception as error:
            print("CCTV 자동 삭제 오류:", error)

        time.sleep(60)



@app.route("/api/admin/cctv", methods=["GET"])
@login_required("admin")
def get_cctv_events():
    db = get_db()

    rows = db.execute("""
        SELECT id, event_type, start_time,
               end_time, expires_at
        FROM cctv_events
        WHERE expires_at > ?
        ORDER BY id DESC
    """, (time.time(),)).fetchall()

    videos = []

    for row in rows:
        video = dict(row)

        video["expires_at"] = datetime.fromtimestamp(
            video["expires_at"]
        ).isoformat(timespec="seconds")

        videos.append(video)

    return jsonify({
        "success": True,
        "videos": videos
    })



def get_cctv_file(event_id):
    db = get_db()

    event = db.execute("""
        SELECT filename
        FROM cctv_events
        WHERE id = ? AND expires_at > ?
    """, (event_id, time.time())).fetchone()

    if event is None:
        abort(404)

    filename = event["filename"]

    if Path(filename).name != filename:
        abort(404)

    path = CAPTURE_DIR / filename

    if not path.is_file():
        abort(404)

    return path


@app.route("/api/admin/cctv/<int:event_id>/video")
@login_required("admin")
def play_cctv(event_id):
    path = get_cctv_file(event_id)

    return send_file(
        path,
        mimetype="video/mp4",
        conditional=True
    )


@app.route("/api/admin/cctv/<int:event_id>/download")
@login_required("admin")
def download_cctv(event_id):
    path = get_cctv_file(event_id)

    return send_file(
        path,
        mimetype="video/mp4",
        as_attachment=True,
        download_name=path.name
    )



@app.route("/api/admin/users", methods=["GET"])
@login_required("admin")
def admin_get_users():
    db = get_db()

    rows = db.execute("""
        SELECT id, username, role, active, created_at
        FROM users
        WHERE role = 'student'
        ORDER BY username ASC, id DESC
    """).fetchall()

    return jsonify({
        "success": True,
        "users": [dict(row) for row in rows]
    })



@app.route(
    "/api/admin/users/<int:user_id>/delete",
    methods=["POST"]
)
@login_required("admin")
def delete_student_account(user_id):
    db = get_db()

    student = db.execute("""
        SELECT id, username, role
        FROM users
        WHERE id = ?
    """, (user_id,)).fetchone()

    if student is None:
        return jsonify({
            "success": False,
            "message": "계정을 찾을 수 없습니다."
        }), 404


    if student["role"] != "student":
        return jsonify({
            "success": False,
            "message": "학생 계정만 삭제할 수 있습니다."
        }), 403

    try:
        db.execute("""
            DELETE FROM appeals
            WHERE student_id = ?
        """, (user_id,))

        
        db.execute("""
            DELETE FROM appeals
            WHERE point_id IN (
                SELECT id FROM points
                WHERE student_id = ?
            )
        """, (user_id,))

        db.execute("""
            DELETE FROM points
            WHERE student_id = ?
        """, (user_id,))

        db.execute("""
            DELETE FROM repairs
            WHERE student_id = ?
        """, (user_id,))

        db.execute("""
            DELETE FROM users
            WHERE id = ? AND role = 'student'
        """, (user_id,))

        db.commit()

    except Exception:
        db.rollback()
        app.logger.exception("학생 계정 삭제 실패")

        return jsonify({
            "success": False,
            "message": "계정 삭제 중 오류가 발생했습니다."
        }), 500

    return jsonify({
        "success": True,
        "message": (
            f"{student['username']} 학생의 계정과 "
            "관련 데이터가 완전히 삭제되었습니다."
        )
    })




def create_render_admin():
    username = os.environ.get("ADMIN_USERNAME")
    password = os.environ.get("ADMIN_PASSWORD")

    if not username or not password:
        return

    with sqlite3.connect(DB_PATH) as db:
        existing = db.execute(
            "SELECT id FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        if existing:
            return

        db.execute("""
            INSERT INTO users
            (username, password_hash, role, active)
            VALUES (?, ?, 'admin', 1)
        """, (
            username,
            generate_password_hash(password)
        ))

        db.commit()


create_render_admin()



if __name__ == "__main__":

    if len(sys.argv) > 1 and sys.argv[1] == "create-admin":
        create_admin()

    else:
        threading.Thread(
            target=cctv_cleanup_worker,
            daemon=True
        ).start()

        app.run(
            host="127.0.0.1",
            port=5000,
            debug=False
        )
