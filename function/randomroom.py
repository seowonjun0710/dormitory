
import sqlite3
import random
from pathlib import Path



BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database.db"

DEFAULT_ROOM_NUMBERS = ["101", "102", "103", "104", "105"]
ROOM_CAPACITY = 4


def connect_db():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"데이터베이스 파일이 없습니다: {DB_PATH}"
        )

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def get_grade(username):
    number = str(username).strip()

    if len(number) != 4 or not number.isdigit():
        raise ValueError(f"잘못된 학번: {username}")

    if number[0] not in ("1", "2", "3"):
        raise ValueError(f"잘못된 학년: {username}")

    return int(number[0])


def init_room_exclusions():
    conn = connect_db()

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS room_exclusions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,

                student_id_1 INTEGER NOT NULL,
                student_id_2 INTEGER NOT NULL,

                CHECK (student_id_1 < student_id_2),

                UNIQUE (student_id_1, student_id_2),

                FOREIGN KEY (student_id_1)
                    REFERENCES users(id),

                FOREIGN KEY (student_id_2)
                    REFERENCES users(id)
            )
        """)

        conn.commit()

    finally:
        conn.close()



def get_students():
    conn = connect_db()

    try:
        rows = conn.execute("""
            SELECT id, username, gender
            FROM users
            WHERE role = 'student'
              AND active = 1
            ORDER BY id
        """).fetchall()

        students = []

        for row in rows:
            student = dict(row)
            student["grade"] = get_grade(student["username"])
            students.append(student)

        return students

    finally:
        conn.close()



def get_room_exclusions():
    init_room_exclusions()

    conn = connect_db()

    try:
        rows = conn.execute("""
            SELECT
                e.id,
                e.student_id_1,
                e.student_id_2,

                u1.username AS student_name_1,
                u2.username AS student_name_2,

                u1.username AS username_1,
                u2.username AS username_2

            FROM room_exclusions e

            JOIN users u1
                ON e.student_id_1 = u1.id

            JOIN users u2
                ON e.student_id_2 = u2.id

            ORDER BY e.id DESC
        """).fetchall()

        return {
            "status": "success",
            "data": [dict(row) for row in rows]
        }

    except sqlite3.Error as e:
        return {
            "status": "error",
            "message": f"금지 규칙 조회 오류: {e}"
        }

    finally:
        conn.close()



def add_room_exclusion(student_id_1, student_id_2):

    if (
        type(student_id_1) is not int
        or type(student_id_2) is not int
        or student_id_1 < 1
        or student_id_2 < 1
    ):
        return {
            "status": "error",
            "message": "올바른 학생 ID를 입력하세요."
        }

    if student_id_1 == student_id_2:
        return {
            "status": "error",
            "message": "같은 학생끼리는 등록할 수 없습니다."
        }

    student_id_1, student_id_2 = sorted(
        (student_id_1, student_id_2)
    )

    init_room_exclusions()
    conn = connect_db()

    try:
        rows = conn.execute("""
            SELECT id
            FROM users
            WHERE id IN (?, ?)
              AND role = 'student'
              AND active = 1
        """, (student_id_1, student_id_2)).fetchall()

        if len(rows) != 2:
            return {
                "status": "error",
                "message": (
                    "두 학생 모두 존재하는 "
                    "활성 학생이어야 합니다."
                )
            }

        cursor = conn.execute("""
            INSERT INTO room_exclusions
            (student_id_1, student_id_2)
            VALUES (?, ?)
        """, (student_id_1, student_id_2))

        conn.commit()

        return {
            "status": "success",
            "message": "같은 방 배정 금지 규칙이 추가되었습니다.",
            "exclusion_id": cursor.lastrowid
        }

    except sqlite3.IntegrityError:
        return {
            "status": "error",
            "message": "이미 등록된 금지 규칙입니다."
        }

    except sqlite3.Error as e:
        return {
            "status": "error",
            "message": f"금지 규칙 추가 오류: {e}"
        }

    finally:
        conn.close()



def delete_room_exclusion(exclusion_id):

    if type(exclusion_id) is not int or exclusion_id < 1:
        return {
            "status": "error",
            "message": "올바른 규칙 번호가 아닙니다."
        }

    init_room_exclusions()
    conn = connect_db()

    try:
        cursor = conn.execute("""
            DELETE FROM room_exclusions
            WHERE id = ?
        """, (exclusion_id,))

        if cursor.rowcount == 0:
            return {
                "status": "error",
                "message": "해당 금지 규칙이 없습니다."
            }

        conn.commit()

        return {
            "status": "success",
            "message": "금지 규칙이 삭제되었습니다."
        }

    except sqlite3.Error as e:
        return {
            "status": "error",
            "message": f"금지 규칙 삭제 오류: {e}"
        }

    finally:
        conn.close()


def clear_room_exclusions():
    init_room_exclusions()

    conn = connect_db()

    try:
        cursor = conn.execute("""
            DELETE FROM room_exclusions
        """)

        deleted_count = cursor.rowcount

        conn.commit()

        return {
            "status": "success",
            "message": f"금지 학생 쌍 {deleted_count}개를 모두 삭제했습니다.",
            "deleted_count": deleted_count
        }

    except sqlite3.Error:
        conn.rollback()

        return {
            "status": "error",
            "message": "금지 학생 쌍 전체 삭제 중 오류가 발생했습니다."
        }

    finally:
        conn.close()


def build_exclusion_map(student_ids, exclusion_rows):

    exclusion_map = {
        student_id: set()
        for student_id in student_ids
    }

    for row in exclusion_rows:
        a = row["student_id_1"]
        b = row["student_id_2"]

        
        if a in exclusion_map and b in exclusion_map:
            exclusion_map[a].add(b)
            exclusion_map[b].add(a)

    return exclusion_map



def find_valid_allocation(students, exclusion_rows, room_numbers=None):

    if room_numbers is None:
        room_numbers = get_room_numbers()

    room_numbers = list(room_numbers)

    if not room_numbers:
        return None

    if len(students) > len(room_numbers) * ROOM_CAPACITY:
        return None

    student_ids = [
        student["id"]
        for student in students
    ]

    exclusion_map = build_exclusion_map(
        student_ids,
        exclusion_rows
    )

    rooms = {
        room: []
        for room in room_numbers
    }

    for student in students:
        if (
            student["grade"] is None
            or not str(student["grade"]).strip()
            or student["gender"] is None
            or not str(student["gender"]).strip()
        ):
            return None

    ordered_students = students[:]
    random.shuffle(ordered_students)

    ordered_students.sort(
        key=lambda student: len(
            exclusion_map[student["id"]]
        ),
        reverse=True
    )

    def can_enter_room(student, room):

        if len(rooms[room]) >= ROOM_CAPACITY:
            return False

        for occupant in rooms[room]:

            if (
                str(occupant["grade"]).strip()
                != str(student["grade"]).strip()
            ):
                return False

            if (
                str(occupant["gender"]).strip()
                != str(student["gender"]).strip()
            ):
                return False

            if (
                occupant["id"]
                in exclusion_map[student["id"]]
            ):
                return False

        return True

    def backtrack(index):

        if index == len(ordered_students):
            return True

        student = ordered_students[index]

        candidate_rooms = sorted(
            room_numbers,
            key=lambda room: (
                0, int(str(room))
            ) if str(room).isdigit() else (
                1, str(room)
            )
        )

        tried_empty_room = False

        for room in candidate_rooms:

            if not rooms[room]:
                if tried_empty_room:
                    continue
                tried_empty_room = True

            if not can_enter_room(student, room):
                continue

            rooms[room].append(student)

            if backtrack(index + 1):
                return True

            rooms[room].pop()

        return False

    if not backtrack(0):
        return None

    assignments = []

    for room in room_numbers:

        occupants = rooms[room][:]
        random.shuffle(occupants)

        for student in occupants:
            assignments.append({
                "student_id": student["id"],
                "username": student["username"],
                "room_number": room
            })

    return assignments



def prepare_allocation(grade, gender):

    if type(grade) is not int or grade not in (1, 2, 3):
        return {
            "status": "error",
            "message": "학년은 1~3학년 중 선택해야 합니다."
        }

    if gender not in ("남", "여"):
        return {
            "status": "error",
            "message": "성별은 남 또는 여 중 선택해야 합니다."
        }

    try:
        all_students = get_students()

        students = [
            student
            for student in all_students
            if student["grade"] == grade
            and student["gender"] == gender
        ]

        if not students:
            return {
                "status": "error",
                "message": "선택한 학년과 성별에 해당하는 학생이 없습니다."
            }

        init_room_exclusions()
        init_rooms()

        conn = connect_db()

        try:
            all_rooms = get_room_numbers()

            occupied_rows = conn.execute("""
                SELECT username, gender, room_number
                FROM users
                WHERE role = 'student'
                  AND room_number IS NOT NULL
            """).fetchall()

            blocked_rooms = set()

            for row in occupied_rows:
                student_grade = get_grade(row["username"])

                if (
                    student_grade != grade
                    or row["gender"] != gender
                ):
                    blocked_rooms.add(row["room_number"])

            available_rooms = [
                room
                for room in all_rooms
                if room not in blocked_rooms
            ]

            if not available_rooms:
                return {
                    "status": "error",
                    "message": "선택한 그룹이 사용할 수 있는 빈 방이 없습니다."
                }

            exclusion_rows = [
                dict(row)
                for row in conn.execute("""
                    SELECT student_id_1, student_id_2
                    FROM room_exclusions
                """).fetchall()
            ]

        finally:
            conn.close()

        max_students = len(available_rooms) * ROOM_CAPACITY

        if len(students) > max_students:
            return {
                "status": "error",
                "message": (
                    f"선택한 그룹은 {len(students)}명인데 "
                    f"배정 가능한 인원은 {max_students}명입니다. "
                    "방을 추가해 주세요."
                )
            }

        assignments = find_valid_allocation(
            students,
            exclusion_rows,
            available_rooms
        )

        if assignments is None:
            return {
                "status": "error",
                "message": (
                    "같은 방 배정 금지 조건을 만족하는 "
                    "배정 결과를 찾지 못했습니다. "
                    "방 개수와 금지 학생 쌍을 확인해 주세요."
                )
            }

        return {
            "status": "success",
            "message": f"{grade}학년 {gender}학생 방 배정 결과가 준비되었습니다.",
            "data": assignments,
            "grade": grade,
            "gender": gender,
            "total_students": len(students),
            "assigned_count": len(assignments),
            "unassigned_count": 0
        }

    except (sqlite3.Error, FileNotFoundError, ValueError) as e:
        return {
            "status": "error",
            "message": f"방 배정 준비 오류: {e}"
        }


def save_allocation(assignments, grade, gender):

    if type(grade) is not int or grade not in (1, 2, 3):
        return {
            "status": "error",
            "message": "올바른 학년을 선택해 주세요."
        }

    if gender not in ("남", "여"):
        return {
            "status": "error",
            "message": "올바른 성별을 선택해 주세요."
        }

    if not isinstance(assignments, list) or not assignments:
        return {
            "status": "error",
            "message": "저장할 배정 결과가 없습니다."
        }

    try:
        init_room_exclusions()
        init_rooms()
        conn = connect_db()
    except (sqlite3.Error, FileNotFoundError) as e:
        return {
            "status": "error",
            "message": f"데이터베이스 연결 오류: {e}"
        }

    try:
        conn.execute("BEGIN IMMEDIATE")

        room_numbers = {
            row["room_number"]
            for row in conn.execute(
                "SELECT room_number FROM rooms"
            ).fetchall()
        }

        if not room_numbers:
            return {
                "status": "error",
                "message": "등록된 방이 없습니다."
            }

        active_rows = conn.execute("""
            SELECT id, username, gender
            FROM users
            WHERE role = 'student'
              AND active = 1
        """).fetchall()

        target_students = {}

        for row in active_rows:
            student_grade = get_grade(row["username"])

            if (
                student_grade == grade
                and row["gender"] == gender
            ):
                target_students[row["id"]] = dict(row)

        if not target_students:
            return {
                "status": "error",
                "message": "선택한 그룹에 학생이 없습니다."
            }

        assigned_rooms = {}
        room_counts = {}

        for assignment in assignments:

            if not isinstance(assignment, dict):
                return {
                    "status": "error",
                    "message": "배정 데이터 형식이 올바르지 않습니다."
                }

            student_id = assignment.get("student_id")
            room = assignment.get("room_number")

            if type(student_id) is not int:
                return {
                    "status": "error",
                    "message": "학생 ID가 올바르지 않습니다."
                }

            if student_id not in target_students:
                return {
                    "status": "error",
                    "message": "다른 그룹의 학생이 포함되어 있습니다."
                }

            if student_id in assigned_rooms:
                return {
                    "status": "error",
                    "message": "중복 배정된 학생이 있습니다."
                }

            if room not in room_numbers:
                return {
                    "status": "error",
                    "message": f"존재하지 않는 방 번호입니다: {room}"
                }

            assigned_rooms[student_id] = room

            room_counts[room] = room_counts.get(room, 0) + 1

            if room_counts[room] > ROOM_CAPACITY:
                return {
                    "status": "error",
                    "message": f"{room}호 정원을 초과했습니다."
                }

        if set(assigned_rooms) != set(target_students):
            return {
                "status": "error",
                "message": (
                    "선택한 그룹의 학생이 누락되었습니다. "
                    "다시 추첨해 주세요."
                )
            }

        occupied_rows = conn.execute("""
            SELECT id, room_number
            FROM users
            WHERE role = 'student'
              AND room_number IS NOT NULL
        """).fetchall()

        blocked_rooms = {
            row["room_number"]
            for row in occupied_rows
            if row["id"] not in target_students
        }

        for room in assigned_rooms.values():
            if room in blocked_rooms:
                return {
                    "status": "error",
                    "message": (
                        f"{room}호는 다른 그룹이 사용 중입니다. "
                        "다시 추첨해 주세요."
                    )
                }

        for rule in conn.execute("""
            SELECT student_id_1, student_id_2
            FROM room_exclusions
        """).fetchall():

            a = rule["student_id_1"]
            b = rule["student_id_2"]

            if (
                a in assigned_rooms
                and b in assigned_rooms
                and assigned_rooms[a] == assigned_rooms[b]
            ):
                return {
                    "status": "error",
                    "message": (
                        "같은 방 배정 금지 규칙을 위반했습니다. "
                        "다시 추첨해 주세요."
                    )
                }

        for student_id in target_students:
            conn.execute("""
                UPDATE users
                SET room_number = NULL
                WHERE id = ?
            """, (student_id,))

        for student_id, room in assigned_rooms.items():
            conn.execute("""
                UPDATE users
                SET room_number = ?
                WHERE id = ?
            """, (room, student_id))

        conn.commit()

        return {
            "status": "success",
            "message": (
                f"{grade}학년 {gender}학생 "
                f"{len(assignments)}명의 방 배정이 저장되었습니다."
            )
        }

    except (sqlite3.Error, ValueError) as e:
        conn.rollback()
        return {
            "status": "error",
            "message": f"방 배정 저장 오류: {e}"
        }

    finally:
        if conn.in_transaction:
            conn.rollback()

        conn.close()



def allocate_rooms_logic(grade, gender):

    result = prepare_allocation(grade, gender)

    if result["status"] != "success":
        return result

    save_result = save_allocation(
        result["data"],
        grade,
        gender
    )

    if save_result["status"] != "success":
        return save_result

    rooms = []

    for room_number in get_room_numbers():

        occupants = [
            assignment["username"]
            for assignment in result["data"]
            if assignment["room_number"] == room_number
        ]

        rooms.append({
            "room_number": room_number,
            "occupants": occupants
        })

    return {
        "status": "success",
        "message": save_result["message"],
        "grade": grade,
        "gender": gender,
        "data": rooms
    }



def reset_room_allocation():
    try:
        conn = connect_db()
    except (sqlite3.Error, FileNotFoundError) as e:
        return {
            "status": "error",
            "message": f"데이터베이스 연결 오류: {e}"
        }

    try:
        conn.execute("BEGIN IMMEDIATE")

        cursor = conn.execute("""
            UPDATE users
            SET room_number = NULL
            WHERE role = 'student'
              AND room_number IS NOT NULL
        """)

        reset_count = cursor.rowcount
        conn.commit()

        return {
            "status": "success",
            "message": (
                f"학생 {reset_count}명의 "
                "방 배정을 초기화했습니다."
            ),
            "reset_count": reset_count
        }

    except sqlite3.Error as e:
        conn.rollback()
        return {
            "status": "error",
            "message": f"방 배정 초기화 오류: {e}"
        }

    finally:
        if conn.in_transaction:
            conn.rollback()
        conn.close()



def swap_student_rooms(student_id_1, student_id_2):

    if (
        type(student_id_1) is not int
        or type(student_id_2) is not int
        or student_id_1 < 1
        or student_id_2 < 1
        or student_id_1 == student_id_2
    ):
        return {
            "status": "error",
            "message": "서로 다른 두 학생을 선택해 주세요."
        }

    try:
        init_room_exclusions()
        init_rooms()
        conn = connect_db()
    except (sqlite3.Error, FileNotFoundError) as e:
        return {
            "status": "error",
            "message": f"데이터베이스 연결 오류: {e}"
        }

    try:
        conn.execute("BEGIN IMMEDIATE")

        students = conn.execute("""
            SELECT id, username, gender, room_number
            FROM users
            WHERE id IN (?, ?)
              AND role = 'student'
              AND active = 1
        """, (student_id_1, student_id_2)).fetchall()

        if len(students) != 2:
            return {
                "status": "error",
                "message": "활성 상태인 두 학생을 선택해야 합니다."
            }

        student_map = {}

        for row in students:
            student = dict(row)
            student["grade"] = get_grade(student["username"])
            student_map[student["id"]] = student

        a = student_map[student_id_1]
        b = student_map[student_id_2]

        room_a = a["room_number"]
        room_b = b["room_number"]

        if not room_a or not room_b:
            return {
                "status": "error",
                "message": "두 학생 모두 방에 배정되어 있어야 합니다."
            }

        room_a = str(room_a)
        room_b = str(room_b)

        if room_a == room_b:
            return {
                "status": "error",
                "message": "이미 같은 방에 있는 학생들입니다."
            }

        valid_rooms = {
            row["room_number"]
            for row in conn.execute("""
                SELECT room_number FROM rooms
            """).fetchall()
        }

        if room_a not in valid_rooms or room_b not in valid_rooms:
            return {
                "status": "error",
                "message": "존재하지 않는 방이 포함되어 있습니다."
            }

        occupants_a = conn.execute("""
            SELECT id, username, gender
            FROM users
            WHERE role = 'student'
              AND room_number = ?
              AND id != ?
        """, (room_a, student_id_1)).fetchall()

        occupants_b = conn.execute("""
            SELECT id, username, gender
            FROM users
            WHERE role = 'student'
              AND room_number = ?
              AND id != ?
        """, (room_b, student_id_2)).fetchall()

        occupants_a = [
            {
                **dict(row),
                "grade": get_grade(row["username"])
            }
            for row in occupants_a
        ]

        occupants_b = [
            {
                **dict(row),
                "grade": get_grade(row["username"])
            }
            for row in occupants_b
        ]

        if len(occupants_a) >= ROOM_CAPACITY or len(occupants_b) >= ROOM_CAPACITY:
            return {"status": "error", "message": "교환 대상 방의 정원을 확인해 주세요."}

        exclusions = conn.execute("""
            SELECT student_id_1, student_id_2
            FROM room_exclusions
        """).fetchall()

        forbidden_pairs = {
            frozenset((
                row["student_id_1"],
                row["student_id_2"]
            ))
            for row in exclusions
        }

        def compatible(student, occupants):

            if (
                student["grade"] is None
                or not str(student["grade"]).strip()
                or student["gender"] is None
                or not str(student["gender"]).strip()
            ):
                return False

            for occupant in occupants:
                if occupant["grade"] is None or occupant["gender"] is None:
                    return False

                if (
                    str(student["grade"]).strip()
                    != str(occupant["grade"]).strip()
                ):
                    return False

                if (
                    str(student["gender"]).strip()
                    != str(occupant["gender"]).strip()
                ):
                    return False

                pair = frozenset((
                    student["id"],
                    occupant["id"]
                ))

                if pair in forbidden_pairs:
                    return False

            return True

        if (
            not compatible(a, occupants_b)
            or not compatible(b, occupants_a)
        ):
            return {
                "status": "error",
                "message": (
                    "학년, 성별 또는 같은 방 배정 금지 "
                    "규칙 때문에 두 학생의 방을 "
                    "교환할 수 없습니다."
                )
            }

        conn.execute("""
            UPDATE users
            SET room_number = ?
            WHERE id = ?
        """, (room_b, student_id_1))

        conn.execute("""
            UPDATE users
            SET room_number = ?
            WHERE id = ?
        """, (room_a, student_id_2))

        conn.commit()

        return {
            "status": "success",
            "message": "두 학생의 방을 교환했습니다.",
            "student_id_1": student_id_1,
            "student_id_2": student_id_2,
            "room_1": room_b,
            "room_2": room_a
        }

    except sqlite3.Error as e:
        conn.rollback()
        return {
            "status": "error",
            "message": f"방 교환 오류: {e}"
        }

    finally:
        if conn.in_transaction:
            conn.rollback()
        conn.close()



def init_rooms():
    conn = connect_db()
    try:
        existed = conn.execute("""
            SELECT 1 FROM sqlite_master
            WHERE type = 'table' AND name = 'rooms'
        """).fetchone() is not None

        conn.execute("""
            CREATE TABLE IF NOT EXISTS rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_number TEXT NOT NULL UNIQUE
            )
        """)
        if not existed:
            conn.executemany("""
                INSERT INTO rooms (room_number) VALUES (?)
            """, [(room,) for room in DEFAULT_ROOM_NUMBERS])
        conn.commit()
    finally:
        conn.close()


def get_room_numbers():
    init_rooms()

    conn = connect_db()

    try:
        rows = conn.execute("""
            SELECT room_number
            FROM rooms
            ORDER BY id
        """).fetchall()

        return [
            row["room_number"]
            for row in rows
        ]

    finally:
        conn.close()


def add_room(room_number):
    room_number = str(room_number).strip()

    if not room_number:
        return {
            "status": "error",
            "message": "방 번호를 입력해 주세요."
        }

    init_rooms()
    conn = connect_db()

    try:
        conn.execute("""
            INSERT INTO rooms (room_number)
            VALUES (?)
        """, (room_number,))

        conn.commit()

        return {
            "status": "success",
            "message": f"{room_number}호가 추가되었습니다."
        }

    except sqlite3.IntegrityError:
        return {
            "status": "error",
            "message": "이미 존재하는 방 번호입니다."
        }

    except sqlite3.Error as e:
        return {
            "status": "error",
            "message": f"방 추가 오류: {e}"
        }

    finally:
        conn.close()


def rename_room(old_number, new_number):
    old_number = str(old_number).strip()
    new_number = str(new_number).strip()

    if not old_number or not new_number:
        return {
            "status": "error",
            "message": "방 번호를 입력해 주세요."
        }

    init_rooms()
    conn = connect_db()

    try:
        conn.execute("BEGIN IMMEDIATE")

        occupied = conn.execute("""
            SELECT COUNT(*)
            FROM users
            WHERE role = 'student'
              AND room_number = ?
        """, (old_number,)).fetchone()[0]

        if occupied > 0:
            return {
                "status": "error",
                "message": (
                    "배정된 학생이 있는 방은 "
                    "번호를 변경할 수 없습니다."
                )
            }

        cursor = conn.execute("""
            UPDATE rooms
            SET room_number = ?
            WHERE room_number = ?
        """, (new_number, old_number))

        if cursor.rowcount == 0:
            return {
                "status": "error",
                "message": "기존 방 번호가 존재하지 않습니다."
            }

        conn.commit()

        return {
            "status": "success",
            "message": (
                f"{old_number}호를 "
                f"{new_number}호로 변경했습니다."
            )
        }

    except sqlite3.IntegrityError:
        return {
            "status": "error",
            "message": "변경할 방 번호가 이미 존재합니다."
        }

    except sqlite3.Error as e:
        return {
            "status": "error",
            "message": f"방 번호 변경 오류: {e}"
        }

    finally:
        if conn.in_transaction:
            conn.rollback()
        conn.close()


def delete_room(room_number):
    room_number = str(room_number).strip()

    init_rooms()
    conn = connect_db()

    try:
        conn.execute("BEGIN IMMEDIATE")

        occupied = conn.execute("""
            SELECT COUNT(*)
            FROM users
            WHERE role = 'student'
              AND room_number = ?
        """, (room_number,)).fetchone()[0]

        if occupied > 0:
            return {
                "status": "error",
                "message": (
                    "배정된 학생이 있는 방은 "
                    "삭제할 수 없습니다."
                )
            }

        cursor = conn.execute("""
            DELETE FROM rooms
            WHERE room_number = ?
        """, (room_number,))

        if cursor.rowcount == 0:
            return {
                "status": "error",
                "message": "해당 방이 존재하지 않습니다."
            }

        conn.commit()

        return {
            "status": "success",
            "message": f"{room_number}호가 삭제되었습니다."
        }

    except sqlite3.Error as e:
        return {
            "status": "error",
            "message": f"방 삭제 오류: {e}"
        }

    finally:
        if conn.in_transaction:
            conn.rollback()
        conn.close()
