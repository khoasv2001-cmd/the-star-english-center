"""
THE STAR ENGLISH CENTER - App quản lý trung tâm
Flask + SQLite + Flask-Login
Phân quyền 6 cấp: admin / director / manager / teacher / parent / student
"""
import os
import sqlite3
from datetime import datetime, date
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    send_from_directory, abort, g
)
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get('DATA_DIR', BASE_DIR)
UPLOAD_DIR = os.path.join(DATA_DIR, 'uploads')
SUBMISSION_DIR = os.path.join(UPLOAD_DIR, 'submissions')
DOC_DIR = os.path.join(UPLOAD_DIR, 'documents')
ASSIGNMENT_FILE_DIR = os.path.join(UPLOAD_DIR, 'assignments')
DB_PATH = os.path.join(DATA_DIR, 'data.db')

for d in (DATA_DIR, UPLOAD_DIR, SUBMISSION_DIR, DOC_DIR, ASSIGNMENT_FILE_DIR):
    os.makedirs(d, exist_ok=True)

ALLOWED_EXT = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'png', 'jpg', 'jpeg', 'zip', 'rar', 'txt', 'mp3', 'mp4'}
MAX_UPLOAD_MB = 50

# ---------- Link mạng xã hội (sửa 2 dòng dưới đây thành link thật của trung tâm) ----------
ZALO_URL = 'https://zalo.me/0900000000'          # TODO: thay bằng link Zalo trung tâm
FANPAGE_URL = 'https://facebook.com/thestar'      # TODO: thay bằng link Fanpage The Star
CENTER_NAME = 'THE STAR ENGLISH CENTER'
CENTER_SLOGAN = 'SPEAK UP - GROW UP!'

# ---------- Ngân hàng câu đố "Nhìn hình đoán chữ" (emoji làm hình) ----------
# level: easy / medium / hard ; answer: từ tiếng Anh ; hint: gợi ý tiếng Việt
QUIZ_QUESTIONS = [
    # ===== DỄ (easy) =====
    {'emoji': '🍎', 'answer': 'apple', 'hint': 'Quả táo', 'level': 'easy'},
    {'emoji': '🍌', 'answer': 'banana', 'hint': 'Quả chuối', 'level': 'easy'},
    {'emoji': '🐱', 'answer': 'cat', 'hint': 'Con mèo', 'level': 'easy'},
    {'emoji': '🐶', 'answer': 'dog', 'hint': 'Con chó', 'level': 'easy'},
    {'emoji': '🐟', 'answer': 'fish', 'hint': 'Con cá', 'level': 'easy'},
    {'emoji': '🐦', 'answer': 'bird', 'hint': 'Con chim', 'level': 'easy'},
    {'emoji': '☀️', 'answer': 'sun', 'hint': 'Mặt trời', 'level': 'easy'},
    {'emoji': '🌙', 'answer': 'moon', 'hint': 'Mặt trăng', 'level': 'easy'},
    {'emoji': '⭐', 'answer': 'star', 'hint': 'Ngôi sao', 'level': 'easy'},
    {'emoji': '🌧️', 'answer': 'rain', 'hint': 'Mưa', 'level': 'easy'},
    {'emoji': '🌈', 'answer': 'rainbow', 'hint': 'Cầu vồng', 'level': 'easy'},
    {'emoji': '🍊', 'answer': 'orange', 'hint': 'Quả cam', 'level': 'easy'},
    {'emoji': '🍇', 'answer': 'grape', 'hint': 'Quả nho', 'level': 'easy'},
    {'emoji': '🍓', 'answer': 'strawberry', 'hint': 'Quả dâu', 'level': 'easy'},
    {'emoji': '🥚', 'answer': 'egg', 'hint': 'Quả trứng', 'level': 'easy'},
    {'emoji': '🍞', 'answer': 'bread', 'hint': 'Bánh mì', 'level': 'easy'},
    {'emoji': '🧀', 'answer': 'cheese', 'hint': 'Phô mai', 'level': 'easy'},
    {'emoji': '🥛', 'answer': 'milk', 'hint': 'Sữa', 'level': 'easy'},
    {'emoji': '☕', 'answer': 'coffee', 'hint': 'Cà phê', 'level': 'easy'},
    {'emoji': '🍵', 'answer': 'tea', 'hint': 'Trà', 'level': 'easy'},
    {'emoji': '🚗', 'answer': 'car', 'hint': 'Ô tô', 'level': 'easy'},
    {'emoji': '🚌', 'answer': 'bus', 'hint': 'Xe buýt', 'level': 'easy'},
    {'emoji': '🚲', 'answer': 'bike', 'hint': 'Xe đạp', 'level': 'easy'},
    {'emoji': '✈️', 'answer': 'plane', 'hint': 'Máy bay', 'level': 'easy'},
    {'emoji': '🚀', 'answer': 'rocket', 'hint': 'Tên lửa', 'level': 'easy'},
    {'emoji': '🏠', 'answer': 'house', 'hint': 'Ngôi nhà', 'level': 'easy'},
    {'emoji': '🌳', 'answer': 'tree', 'hint': 'Cái cây', 'level': 'easy'},
    {'emoji': '🌸', 'answer': 'flower', 'hint': 'Bông hoa', 'level': 'easy'},
    {'emoji': '🔥', 'answer': 'fire', 'hint': 'Lửa', 'level': 'easy'},
    {'emoji': '💧', 'answer': 'water', 'hint': 'Nước', 'level': 'easy'},
    {'emoji': '❄️', 'answer': 'snow', 'hint': 'Tuyết', 'level': 'easy'},
    {'emoji': '🍦', 'answer': 'ice cream', 'hint': 'Kem', 'level': 'easy'},
    {'emoji': '🎂', 'answer': 'cake', 'hint': 'Bánh kem', 'level': 'easy'},
    {'emoji': '🍕', 'answer': 'pizza', 'hint': 'Bánh pizza', 'level': 'easy'},
    {'emoji': '🐮', 'answer': 'cow', 'hint': 'Con bò', 'level': 'easy'},
    {'emoji': '🐷', 'answer': 'pig', 'hint': 'Con heo', 'level': 'easy'},
    {'emoji': '🐔', 'answer': 'chicken', 'hint': 'Con gà', 'level': 'easy'},
    # ===== TRUNG BÌNH (medium) =====
    {'emoji': '🦒', 'answer': 'giraffe', 'hint': 'Hươu cao cổ', 'level': 'medium'},
    {'emoji': '🐘', 'answer': 'elephant', 'hint': 'Con voi', 'level': 'medium'},
    {'emoji': '🦁', 'answer': 'lion', 'hint': 'Sư tử', 'level': 'medium'},
    {'emoji': '🐯', 'answer': 'tiger', 'hint': 'Con hổ', 'level': 'medium'},
    {'emoji': '🐻', 'answer': 'bear', 'hint': 'Con gấu', 'level': 'medium'},
    {'emoji': '🐼', 'answer': 'panda', 'hint': 'Gấu trúc', 'level': 'medium'},
    {'emoji': '🐨', 'answer': 'koala', 'hint': 'Gấu koala', 'level': 'medium'},
    {'emoji': '🐸', 'answer': 'frog', 'hint': 'Con ếch', 'level': 'medium'},
    {'emoji': '🦋', 'answer': 'butterfly', 'hint': 'Con bướm', 'level': 'medium'},
    {'emoji': '🐝', 'answer': 'bee', 'hint': 'Con ong', 'level': 'medium'},
    {'emoji': '🐍', 'answer': 'snake', 'hint': 'Con rắn', 'level': 'medium'},
    {'emoji': '🐢', 'answer': 'turtle', 'hint': 'Con rùa', 'level': 'medium'},
    {'emoji': '🦈', 'answer': 'shark', 'hint': 'Cá mập', 'level': 'medium'},
    {'emoji': '🐙', 'answer': 'octopus', 'hint': 'Bạch tuộc', 'level': 'medium'},
    {'emoji': '🦀', 'answer': 'crab', 'hint': 'Con cua', 'level': 'medium'},
    {'emoji': '🍉', 'answer': 'watermelon', 'hint': 'Dưa hấu', 'level': 'medium'},
    {'emoji': '🍍', 'answer': 'pineapple', 'hint': 'Quả dứa', 'level': 'medium'},
    {'emoji': '🥕', 'answer': 'carrot', 'hint': 'Cà rốt', 'level': 'medium'},
    {'emoji': '🌽', 'answer': 'corn', 'hint': 'Bắp ngô', 'level': 'medium'},
    {'emoji': '🍄', 'answer': 'mushroom', 'hint': 'Cây nấm', 'level': 'medium'},
    {'emoji': '🌻', 'answer': 'sunflower', 'hint': 'Hoa hướng dương', 'level': 'medium'},
    {'emoji': '🎸', 'answer': 'guitar', 'hint': 'Đàn ghi-ta', 'level': 'medium'},
    {'emoji': '🎹', 'answer': 'piano', 'hint': 'Đàn piano', 'level': 'medium'},
    {'emoji': '🎺', 'answer': 'trumpet', 'hint': 'Kèn trumpet', 'level': 'medium'},
    {'emoji': '🥁', 'answer': 'drum', 'hint': 'Cái trống', 'level': 'medium'},
    {'emoji': '⚽', 'answer': 'football', 'hint': 'Bóng đá', 'level': 'medium'},
    {'emoji': '🏀', 'answer': 'basketball', 'hint': 'Bóng rổ', 'level': 'medium'},
    {'emoji': '🎾', 'answer': 'tennis', 'hint': 'Quần vợt', 'level': 'medium'},
    {'emoji': '🏊', 'answer': 'swimming', 'hint': 'Bơi lội', 'level': 'medium'},
    {'emoji': '🚁', 'answer': 'helicopter', 'hint': 'Trực thăng', 'level': 'medium'},
    {'emoji': '⛵', 'answer': 'sailboat', 'hint': 'Thuyền buồm', 'level': 'medium'},
    {'emoji': '🏰', 'answer': 'castle', 'hint': 'Lâu đài', 'level': 'medium'},
    {'emoji': '🌋', 'answer': 'volcano', 'hint': 'Núi lửa', 'level': 'medium'},
    {'emoji': '🗻', 'answer': 'mountain', 'hint': 'Ngọn núi', 'level': 'medium'},
    # ===== KHÓ (hard) =====
    {'emoji': '🔬', 'answer': 'microscope', 'hint': 'Kính hiển vi', 'level': 'hard'},
    {'emoji': '🔭', 'answer': 'telescope', 'hint': 'Kính thiên văn', 'level': 'hard'},
    {'emoji': '🧲', 'answer': 'magnet', 'hint': 'Nam châm', 'level': 'hard'},
    {'emoji': '🦕', 'answer': 'dinosaur', 'hint': 'Khủng long', 'level': 'hard'},
    {'emoji': '🐉', 'answer': 'dragon', 'hint': 'Con rồng', 'level': 'hard'},
    {'emoji': '🦄', 'answer': 'unicorn', 'hint': 'Kỳ lân', 'level': 'hard'},
    {'emoji': '🎻', 'answer': 'violin', 'hint': 'Đàn vĩ cầm', 'level': 'hard'},
    {'emoji': '🎷', 'answer': 'saxophone', 'hint': 'Kèn saxophone', 'level': 'hard'},
    {'emoji': '🏛️', 'answer': 'museum', 'hint': 'Bảo tàng', 'level': 'hard'},
    {'emoji': '🌌', 'answer': 'galaxy', 'hint': 'Thiên hà', 'level': 'hard'},
    {'emoji': '🪐', 'answer': 'planet', 'hint': 'Hành tinh', 'level': 'hard'},
    {'emoji': '☄️', 'answer': 'comet', 'hint': 'Sao chổi', 'level': 'hard'},
    {'emoji': '🩺', 'answer': 'stethoscope', 'hint': 'Ống nghe y tế', 'level': 'hard'},
    {'emoji': '🧪', 'answer': 'laboratory', 'hint': 'Phòng thí nghiệm', 'level': 'hard'},
    {'emoji': '🛰️', 'answer': 'satellite', 'hint': 'Vệ tinh', 'level': 'hard'},
    {'emoji': '🧭', 'answer': 'compass', 'hint': 'La bàn', 'level': 'hard'},
    {'emoji': '⚓', 'answer': 'anchor', 'hint': 'Mỏ neo', 'level': 'hard'},
    {'emoji': '🏺', 'answer': 'vase', 'hint': 'Bình gốm', 'level': 'hard'},
    {'emoji': '🔱', 'answer': 'trident', 'hint': 'Đinh ba', 'level': 'hard'},
    {'emoji': '🧳', 'answer': 'luggage', 'hint': 'Hành lý', 'level': 'hard'},
    {'emoji': '🪙', 'answer': 'coin', 'hint': 'Đồng xu', 'level': 'hard'},
    {'emoji': '🦴', 'answer': 'skeleton', 'hint': 'Bộ xương', 'level': 'hard'},
    {'emoji': '🫁', 'answer': 'lungs', 'hint': 'Lá phổi', 'level': 'hard'},
    {'emoji': '🫀', 'answer': 'heart', 'hint': 'Trái tim', 'level': 'hard'},
    {'emoji': '🦷', 'answer': 'tooth', 'hint': 'Cái răng', 'level': 'hard'},
    {'emoji': '🧠', 'answer': 'brain', 'hint': 'Bộ não', 'level': 'hard'},
    {'emoji': '🪃', 'answer': 'boomerang', 'hint': 'Boomerang', 'level': 'hard'},
    {'emoji': '🪂', 'answer': 'parachute', 'hint': 'Dù nhảy', 'level': 'hard'},
    {'emoji': '🧯', 'answer': 'extinguisher', 'hint': 'Bình chữa cháy', 'level': 'hard'},
]

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'thestar-change-me-in-production')
app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_MB * 1024 * 1024

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Vui lòng đăng nhập để tiếp tục.'

# ---------- Vai trò ----------
ROLES = {
    'admin':    'Admin',
    'director': 'Giám đốc trung tâm',
    'manager':  'Quản lý lớp',
    'teacher':  'Giáo viên',
    'parent':   'Phụ huynh',
    'student':  'Học sinh',
}
# Cấp bậc để so sánh quyền (số lớn = quyền rộng hơn)
ROLE_RANK = {'student': 1, 'parent': 1, 'teacher': 2, 'manager': 3, 'director': 4, 'admin': 5}
ATTENDANCE_LABELS = {'present': 'Có mặt', 'absent': 'Vắng', 'late': 'Đi muộn', 'excused': 'Có phép'}
TUITION_LABELS = {'unpaid': 'Chưa đóng', 'partial': 'Đóng một phần', 'paid': 'Đã đóng'}
# Các thứ trong tuần để tick chọn lịch học
WEEKDAYS = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật']
MAX_PARENTS_PER_STUDENT = 2
MAX_STUDENTS_PER_PARENT = 5


# ---------- DB ----------
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute('PRAGMA foreign_keys = ON')
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT,
        email TEXT,
        phone TEXT,
        role TEXT NOT NULL DEFAULT 'student',
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS classes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        level TEXT,
        schedule TEXT,
        room TEXT,
        manager_id INTEGER,
        teacher_id INTEGER,
        note TEXT,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        FOREIGN KEY(manager_id) REFERENCES users(id) ON DELETE SET NULL,
        FOREIGN KEY(teacher_id) REFERENCES users(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT,
        full_name TEXT NOT NULL,
        dob TEXT,
        gender TEXT,
        phone TEXT,
        address TEXT,
        class_id INTEGER,
        parent_id INTEGER,
        student_user_id INTEGER,
        monthly_fee REAL DEFAULT 0,
        note TEXT,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE SET NULL,
        FOREIGN KEY(parent_id) REFERENCES users(id) ON DELETE SET NULL,
        FOREIGN KEY(student_user_id) REFERENCES users(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_id INTEGER NOT NULL,
        teacher_id INTEGER,
        title TEXT NOT NULL,
        description TEXT,
        due_date TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE,
        FOREIGN KEY(teacher_id) REFERENCES users(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assignment_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        content TEXT,
        file_path TEXT,
        file_name TEXT,
        submitted_at TEXT,
        status TEXT NOT NULL DEFAULT 'pending',
        score REAL,
        feedback TEXT,
        graded_at TEXT,
        UNIQUE(assignment_id, student_id),
        FOREIGN KEY(assignment_id) REFERENCES assignments(id) ON DELETE CASCADE,
        FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        class_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'present',
        note TEXT,
        created_by INTEGER,
        created_at TEXT NOT NULL,
        UNIQUE(student_id, date),
        FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE,
        FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS tuition (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL,
        period TEXT NOT NULL,
        amount REAL DEFAULT 0,
        paid_amount REAL DEFAULT 0,
        due_date TEXT,
        status TEXT NOT NULL DEFAULT 'unpaid',
        note TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        file_path TEXT,
        file_name TEXT,
        class_id INTEGER,
        uploaded_by INTEGER,
        created_at TEXT NOT NULL,
        FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE,
        FOREIGN KEY(uploaded_by) REFERENCES users(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS assignment_files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assignment_id INTEGER NOT NULL,
        file_path TEXT NOT NULL,
        file_name TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(assignment_id) REFERENCES assignments(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS student_parents (
        student_id INTEGER NOT NULL,
        parent_id INTEGER NOT NULL,
        PRIMARY KEY(student_id, parent_id),
        FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE,
        FOREIGN KEY(parent_id) REFERENCES users(id) ON DELETE CASCADE
    );
    ''')
    # Chuyển dữ liệu phụ huynh cũ (students.parent_id) sang bảng liên kết nhiều-nhiều
    conn.execute('''INSERT OR IGNORE INTO student_parents (student_id, parent_id)
        SELECT id, parent_id FROM students WHERE parent_id IS NOT NULL''')

    # Migration: thêm cột phê duyệt cho phiếu học phí (nếu chưa có)
    existing_cols = [r[1] for r in conn.execute("PRAGMA table_info(tuition)").fetchall()]
    for col, ddl in (
        ('approved', 'ALTER TABLE tuition ADD COLUMN approved INTEGER NOT NULL DEFAULT 0'),
        ('approved_by', 'ALTER TABLE tuition ADD COLUMN approved_by INTEGER'),
        ('approved_at', 'ALTER TABLE tuition ADD COLUMN approved_at TEXT'),
        ('created_by', 'ALTER TABLE tuition ADD COLUMN created_by INTEGER'),
    ):
        if col not in existing_cols:
            conn.execute(ddl)
    # Các phiếu cũ (đã tồn tại trước khi có tính năng duyệt) coi như đã được duyệt
    if 'approved' not in existing_cols:
        conn.execute('UPDATE tuition SET approved=1')
    conn.commit()

    # Tạo tài khoản admin mặc định nếu chưa có user nào
    cur = conn.execute('SELECT COUNT(*) FROM users')
    if cur.fetchone()[0] == 0:
        now = datetime.now().isoformat()
        conn.execute(
            'INSERT INTO users (username, password_hash, full_name, role, active, created_at) VALUES (?,?,?,?,1,?)',
            ('admin', generate_password_hash('admin123'), 'Quản trị viên', 'admin', now)
        )
        conn.commit()
    conn.close()


# ---------- Flask-Login ----------
class User(UserMixin):
    def __init__(self, row):
        self.id = row['id']
        self.username = row['username']
        self.full_name = row['full_name']
        self.email = row['email']
        self.phone = row['phone']
        self.role = row['role']
        self.active = row['active']

    @property
    def role_label(self):
        return ROLES.get(self.role, self.role)


@login_manager.user_loader
def load_user(user_id):
    row = get_db().execute('SELECT * FROM users WHERE id=? AND active=1', (user_id,)).fetchone()
    return User(row) if row else None


def roles_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return login_manager.unauthorized()
            if current_user.role not in roles:
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator


def has_role(*roles):
    return current_user.is_authenticated and current_user.role in roles


@app.context_processor
def inject_globals():
    return dict(
        ROLES=ROLES, ROLE_RANK=ROLE_RANK,
        ATTENDANCE_LABELS=ATTENDANCE_LABELS, TUITION_LABELS=TUITION_LABELS,
        has_role=has_role, today=date.today().isoformat(), WEEKDAYS=WEEKDAYS,
        ZALO_URL=ZALO_URL, FANPAGE_URL=FANPAGE_URL,
        CENTER_NAME=CENTER_NAME, CENTER_SLOGAN=CENTER_SLOGAN
    )


# ---------- Helpers phân quyền dữ liệu ----------
def get_student_record_for_user():
    """Học sinh đang đăng nhập tương ứng với bản ghi students nào."""
    if current_user.role != 'student':
        return None
    return get_db().execute(
        'SELECT * FROM students WHERE student_user_id=?', (current_user.id,)
    ).fetchone()


def visible_class_ids():
    """Danh sách id lớp mà người dùng hiện tại được xem."""
    db = get_db()
    role = current_user.role
    if role in ('admin', 'director'):
        rows = db.execute('SELECT id FROM classes').fetchall()
    elif role == 'manager':
        rows = db.execute('SELECT id FROM classes WHERE manager_id=?', (current_user.id,)).fetchall()
    elif role == 'teacher':
        rows = db.execute('SELECT id FROM classes WHERE teacher_id=?', (current_user.id,)).fetchall()
    elif role == 'parent':
        rows = db.execute(
            '''SELECT DISTINCT s.class_id AS id FROM students s
               JOIN student_parents sp ON sp.student_id=s.id
               WHERE sp.parent_id=? AND s.class_id IS NOT NULL''',
            (current_user.id,)).fetchall()
    elif role == 'student':
        rows = db.execute(
            'SELECT class_id AS id FROM students WHERE student_user_id=? AND class_id IS NOT NULL',
            (current_user.id,)).fetchall()
    else:
        rows = []
    return [r['id'] for r in rows]


def can_view_class(class_id):
    if has_role('admin', 'director'):
        return True
    return class_id in visible_class_ids()


def can_manage_class(class_id):
    """Được sửa lớp / giao bài / điểm danh."""
    db = get_db()
    if has_role('admin', 'director'):
        return True
    row = db.execute('SELECT manager_id, teacher_id FROM classes WHERE id=?', (class_id,)).fetchone()
    if not row:
        return False
    return current_user.id in (row['manager_id'], row['teacher_id'])


def visible_student_ids():
    db = get_db()
    role = current_user.role
    if role in ('admin', 'director'):
        rows = db.execute('SELECT id FROM students').fetchall()
        return [r['id'] for r in rows]
    if role == 'parent':
        rows = db.execute('SELECT student_id AS id FROM student_parents WHERE parent_id=?',
                          (current_user.id,)).fetchall()
        return [r['id'] for r in rows]
    if role == 'student':
        rows = db.execute('SELECT id FROM students WHERE student_user_id=?', (current_user.id,)).fetchall()
        return [r['id'] for r in rows]
    # manager / teacher: học sinh trong các lớp họ phụ trách
    cids = visible_class_ids()
    if not cids:
        return []
    q = 'SELECT id FROM students WHERE class_id IN (%s)' % ','.join('?' * len(cids))
    rows = db.execute(q, cids).fetchall()
    return [r['id'] for r in rows]


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


def recalc_tuition_status(row_amount, paid):
    if paid <= 0:
        return 'unpaid'
    if paid < row_amount:
        return 'partial'
    return 'paid'


def parents_of_student(sid):
    """Danh sách tài khoản phụ huynh đang gắn với học sinh."""
    return get_db().execute(
        '''SELECT u.* FROM users u JOIN student_parents sp ON sp.parent_id=u.id
           WHERE sp.student_id=? ORDER BY u.full_name''', (sid,)).fetchall()


def parent_ids_of_student(sid):
    rows = get_db().execute('SELECT parent_id FROM student_parents WHERE student_id=?', (sid,)).fetchall()
    return [r['parent_id'] for r in rows]


def set_student_parents(sid, parent_ids):
    """Gán lại danh sách phụ huynh cho học sinh. Trả về (ok, thông_báo_lỗi)."""
    db = get_db()
    # Lọc trùng và giá trị rỗng, giới hạn số phụ huynh
    clean = []
    for pid in parent_ids:
        if pid and pid not in clean:
            clean.append(pid)
    if len(clean) > MAX_PARENTS_PER_STUDENT:
        return False, f'Mỗi học sinh chỉ gắn tối đa {MAX_PARENTS_PER_STUDENT} phụ huynh.'
    # Kiểm tra mỗi phụ huynh không vượt quá số con cho phép
    for pid in clean:
        cnt = db.execute(
            'SELECT COUNT(*) c FROM student_parents WHERE parent_id=? AND student_id<>?',
            (pid, sid)).fetchone()['c']
        if cnt >= MAX_STUDENTS_PER_PARENT:
            p = db.execute('SELECT full_name FROM users WHERE id=?', (pid,)).fetchone()
            name = p['full_name'] if p else pid
            return False, f'Phụ huynh "{name}" đã theo dõi đủ {MAX_STUDENTS_PER_PARENT} học sinh.'
    db.execute('DELETE FROM student_parents WHERE student_id=?', (sid,))
    for pid in clean:
        db.execute('INSERT OR IGNORE INTO student_parents (student_id, parent_id) VALUES (?,?)', (sid, pid))
    # Giữ students.parent_id = phụ huynh đầu tiên để tương thích hiển thị cũ
    db.execute('UPDATE students SET parent_id=? WHERE id=?', (clean[0] if clean else None, sid))
    return True, None


def visible_document_ids():
    """Id tài liệu mà người dùng hiện tại được xem."""
    db = get_db()
    if has_role('admin', 'director'):
        rows = db.execute('SELECT id FROM documents').fetchall()
        return [r['id'] for r in rows]
    cids = visible_class_ids()
    # Tài liệu chung (class_id IS NULL) ai cũng xem được
    if cids:
        q = 'SELECT id FROM documents WHERE class_id IS NULL OR class_id IN (%s)' % ','.join('?' * len(cids))
        rows = db.execute(q, cids).fetchall()
    else:
        rows = db.execute('SELECT id FROM documents WHERE class_id IS NULL').fetchall()
    return [r['id'] for r in rows]


# ============================================================
#  AUTH
# ============================================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        row = get_db().execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        if row and row['active'] and check_password_hash(row['password_hash'], password):
            login_user(User(row))
            return redirect(url_for('dashboard'))
        flash('Sai tên đăng nhập hoặc mật khẩu.', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/doi-mat-khau', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        old = request.form.get('old_password', '')
        new = request.form.get('new_password', '')
        confirm = request.form.get('confirm_password', '')
        db = get_db()
        row = db.execute('SELECT password_hash FROM users WHERE id=?', (current_user.id,)).fetchone()
        if not check_password_hash(row['password_hash'], old):
            flash('Mật khẩu cũ không đúng.', 'danger')
        elif len(new) < 6:
            flash('Mật khẩu mới phải từ 6 ký tự.', 'danger')
        elif new != confirm:
            flash('Xác nhận mật khẩu không khớp.', 'danger')
        else:
            db.execute('UPDATE users SET password_hash=? WHERE id=?',
                       (generate_password_hash(new), current_user.id))
            db.commit()
            flash('Đã đổi mật khẩu.', 'success')
            return redirect(url_for('dashboard'))
    return render_template('change_password.html')


# ============================================================
#  DASHBOARD / BÁO CÁO
# ============================================================
def _overview_stats(sids, cids, class_filter='', age_filter=''):
    """Tổng quan học phí/doanh thu theo phân khúc lớp và độ tuổi.
    sids/cids: phạm vi học sinh & lớp được phép xem (None = tất cả)."""
    db = get_db()
    # Lấy danh sách học sinh kèm học phí trong phạm vi cho phép
    sql = '''SELECT s.id, s.dob, s.class_id, c.name class_name,
        COALESCE((SELECT SUM(amount) FROM tuition t WHERE t.student_id=s.id AND t.approved=1),0) billed,
        COALESCE((SELECT SUM(paid_amount) FROM tuition t WHERE t.student_id=s.id AND t.approved=1),0) paid
        FROM students s LEFT JOIN classes c ON c.id=s.class_id WHERE s.active=1'''
    params = []
    if sids is not None:
        if not sids:
            return dict(total_students=0, total_classes=len(cids or []), total_teachers=0,
                        tuition_total=0, tuition_paid=0, tuition_due=0,
                        by_class=[], by_age=[], classes=[],
                        class_filter=class_filter, age_filter=age_filter, age_groups=[])
        sql += ' AND s.id IN (%s)' % ','.join('?' * len(sids))
        params += list(sids)
    rows = db.execute(sql, params).fetchall()

    by_class = {}
    by_age = {}
    total_students = 0
    t_billed = t_paid = 0
    for r in rows:
        grp = _age_group(_age_from_dob(r['dob']))
        # Áp dụng bộ lọc phân khúc
        if class_filter and str(r['class_id']) != class_filter:
            continue
        if age_filter and grp != age_filter:
            continue
        total_students += 1
        t_billed += r['billed']
        t_paid += r['paid']
        cn = r['class_name'] or 'Chưa xếp lớp'
        c = by_class.setdefault(cn, {'name': cn, 'count': 0, 'billed': 0, 'paid': 0})
        c['count'] += 1; c['billed'] += r['billed']; c['paid'] += r['paid']
        a = by_age.setdefault(grp, {'name': grp, 'count': 0, 'billed': 0, 'paid': 0})
        a['count'] += 1; a['billed'] += r['billed']; a['paid'] += r['paid']

    age_order = ['Mầm non (≤5)', 'Tiểu học (6-10)', 'THCS (11-15)', 'THPT+ (16+)', 'Chưa rõ tuổi']
    by_age_list = [by_age[k] for k in age_order if k in by_age]
    by_class_list = sorted(by_class.values(), key=lambda x: x['name'])

    total_classes = len(cids) if cids is not None else \
        db.execute('SELECT COUNT(*) c FROM classes WHERE active=1').fetchone()['c']
    total_teachers = db.execute("SELECT COUNT(*) c FROM users WHERE role='teacher' AND active=1").fetchone()['c']

    return dict(
        total_students=total_students, total_classes=total_classes, total_teachers=total_teachers,
        tuition_total=t_billed, tuition_paid=t_paid, tuition_due=t_billed - t_paid,
        by_class=by_class_list, by_age=by_age_list,
        class_filter=class_filter, age_filter=age_filter,
        age_groups=[g for g in age_order if g != 'Chưa rõ tuổi'],
    )


@app.route('/')
@login_required
def dashboard():
    db = get_db()
    role = current_user.role
    stats = {}

    # Tổng quan có học phí & doanh thu phân khúc: chỉ Giám đốc/Admin và Quản lý
    if role in ('admin', 'director', 'manager'):
        class_filter = request.args.get('class_id', '')
        age_filter = request.args.get('age_group', '')
        if role in ('admin', 'director'):
            sids = None  # tất cả học sinh
            cids = None
            stats = _overview_stats(sids, cids, class_filter, age_filter)
            stats['classes'] = db.execute('''
                SELECT c.*, u.full_name teacher_name,
                  (SELECT COUNT(*) FROM students s WHERE s.class_id=c.id AND s.active=1) student_count
                FROM classes c LEFT JOIN users u ON u.id=c.teacher_id
                WHERE c.active=1 ORDER BY c.name''').fetchall()
            class_choices = db.execute('SELECT id, name FROM classes WHERE active=1 ORDER BY name').fetchall()
        else:  # manager — chỉ phạm vi lớp mình phụ trách
            cids = visible_class_ids()
            sids = visible_student_ids()
            stats = _overview_stats(sids, cids, class_filter, age_filter)
            if cids:
                qc = '''SELECT c.*, u.full_name teacher_name,
                    (SELECT COUNT(*) FROM students s WHERE s.class_id=c.id AND s.active=1) student_count
                    FROM classes c LEFT JOIN users u ON u.id=c.teacher_id
                    WHERE c.id IN (%s) ORDER BY c.name''' % ','.join('?' * len(cids))
                stats['classes'] = db.execute(qc, cids).fetchall()
                class_choices = db.execute(
                    'SELECT id, name FROM classes WHERE id IN (%s) ORDER BY name' % ','.join('?' * len(cids)),
                    cids).fetchall()
            else:
                stats['classes'] = []
                class_choices = []
        return render_template('dashboard_director.html', stats=stats, class_choices=class_choices)

    if role == 'teacher':
        cids = visible_class_ids()
        sids = visible_student_ids()
        stats['my_classes'] = len(cids)
        stats['my_students'] = len(sids)
        stats['assignments'] = 0
        if cids:
            q = 'SELECT COUNT(*) c FROM assignments WHERE class_id IN (%s)' % ','.join('?' * len(cids))
            stats['assignments'] = db.execute(q, cids).fetchone()['c']
            qc = 'SELECT * FROM classes WHERE id IN (%s) ORDER BY name' % ','.join('?' * len(cids))
            stats['classes'] = db.execute(qc, cids).fetchall()
        else:
            stats['classes'] = []
        return render_template('dashboard_staff.html', stats=stats)

    if role == 'parent':
        children = db.execute('''
            SELECT s.*, c.name class_name FROM students s
            JOIN student_parents sp ON sp.student_id=s.id
            LEFT JOIN classes c ON c.id=s.class_id
            WHERE sp.parent_id=? ORDER BY s.full_name''', (current_user.id,)).fetchall()
        return render_template('dashboard_parent.html', children=children)

    # student
    srow = get_student_record_for_user()
    info = None
    assignments = []
    if srow:
        info = db.execute('''SELECT s.*, c.name class_name FROM students s
            LEFT JOIN classes c ON c.id=s.class_id WHERE s.id=?''', (srow['id'],)).fetchone()
        if srow['class_id']:
            assignments = db.execute('''
                SELECT a.*, sub.status sub_status, sub.score FROM assignments a
                LEFT JOIN submissions sub ON sub.assignment_id=a.id AND sub.student_id=?
                WHERE a.class_id=? ORDER BY a.due_date DESC LIMIT 10''',
                (srow['id'], srow['class_id'])).fetchall()
    return render_template('dashboard_student.html', info=info, assignments=assignments)


# ============================================================
#  QUẢN LÝ NGƯỜI DÙNG (admin)
# ============================================================
# Vai trò mà quản lý lớp được phép tạo (admin tạo được tất cả)
MANAGER_CREATABLE_ROLES = ('student', 'parent')


@app.route('/nguoi-dung')
@roles_required('admin', 'manager')
def users_list():
    db = get_db()
    role_filter = request.args.get('role', '')
    # Quản lý lớp chỉ thấy tài khoản học sinh & phụ huynh
    if has_role('manager'):
        if role_filter not in MANAGER_CREATABLE_ROLES:
            role_filter = ''
        if role_filter:
            rows = db.execute('SELECT * FROM users WHERE role=? ORDER BY full_name', (role_filter,)).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM users WHERE role IN ('student','parent') ORDER BY role, full_name").fetchall()
    elif role_filter:
        rows = db.execute('SELECT * FROM users WHERE role=? ORDER BY full_name', (role_filter,)).fetchall()
    else:
        rows = db.execute('SELECT * FROM users ORDER BY role, full_name').fetchall()
    return render_template('users.html', users=rows, role_filter=role_filter)


@app.route('/nguoi-dung/them', methods=['GET', 'POST'])
@roles_required('admin', 'manager')
def user_create():
    db = get_db()
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'student')
        # Quản lý lớp chỉ được tạo tài khoản học sinh / phụ huynh
        if has_role('manager') and role not in MANAGER_CREATABLE_ROLES:
            abort(403)
        if not username or not password:
            flash('Cần nhập tên đăng nhập và mật khẩu.', 'danger')
        elif db.execute('SELECT 1 FROM users WHERE username=?', (username,)).fetchone():
            flash('Tên đăng nhập đã tồn tại.', 'danger')
        else:
            db.execute('''INSERT INTO users (username, password_hash, full_name, email, phone, role, created_at)
                VALUES (?,?,?,?,?,?,?)''',
                (username, generate_password_hash(password), request.form.get('full_name'),
                 request.form.get('email'), request.form.get('phone'), role, datetime.now().isoformat()))
            db.commit()
            flash('Đã tạo tài khoản.', 'success')
            return redirect(url_for('users_list'))
    return render_template('user_form.html', user=None)


@app.route('/nguoi-dung/<int:uid>/sua', methods=['GET', 'POST'])
@roles_required('admin')
def user_edit(uid):
    db = get_db()
    row = db.execute('SELECT * FROM users WHERE id=?', (uid,)).fetchone()
    if not row:
        abort(404)
    if request.method == 'POST':
        db.execute('''UPDATE users SET full_name=?, email=?, phone=?, role=?, active=? WHERE id=?''',
                   (request.form.get('full_name'), request.form.get('email'), request.form.get('phone'),
                    request.form.get('role'), 1 if request.form.get('active') else 0, uid))
        new_pw = request.form.get('password', '')
        if new_pw:
            db.execute('UPDATE users SET password_hash=? WHERE id=?', (generate_password_hash(new_pw), uid))
        db.commit()
        flash('Đã cập nhật tài khoản.', 'success')
        return redirect(url_for('users_list'))
    return render_template('user_form.html', user=row)


# ============================================================
#  LỚP HỌC
# ============================================================
@app.route('/lop-hoc')
@roles_required('admin', 'director', 'manager', 'teacher')
def classes_list():
    db = get_db()
    if has_role('admin', 'director'):
        rows = db.execute('''SELECT c.*, u.full_name teacher_name, m.full_name manager_name,
            (SELECT COUNT(*) FROM students s WHERE s.class_id=c.id AND s.active=1) student_count
            FROM classes c LEFT JOIN users u ON u.id=c.teacher_id
            LEFT JOIN users m ON m.id=c.manager_id ORDER BY c.name''').fetchall()
    else:
        cids = visible_class_ids()
        if cids:
            q = '''SELECT c.*, u.full_name teacher_name, m.full_name manager_name,
                (SELECT COUNT(*) FROM students s WHERE s.class_id=c.id AND s.active=1) student_count
                FROM classes c LEFT JOIN users u ON u.id=c.teacher_id
                LEFT JOIN users m ON m.id=c.manager_id
                WHERE c.id IN (%s) ORDER BY c.name''' % ','.join('?' * len(cids))
            rows = db.execute(q, cids).fetchall()
        else:
            rows = []
    return render_template('classes_list.html', classes=rows)


def _build_schedule():
    """Ghép lịch học từ các thứ được tick + giờ học thành chuỗi."""
    days = request.form.getlist('days')
    days = [d for d in WEEKDAYS if d in days]  # giữ đúng thứ tự trong tuần
    time = (request.form.get('time') or '').strip()
    parts = []
    if days:
        parts.append(', '.join(days))
    if time:
        parts.append(time)
    return ' · '.join(parts)


def _build_dob():
    """Ghép ngày sinh từ 3 ô chọn ngày / tháng / năm thành chuỗi YYYY-MM-DD."""
    d = request.form.get('dob_day', '')
    m = request.form.get('dob_month', '')
    y = request.form.get('dob_year', '')
    if d and m and y:
        try:
            return date(int(y), int(m), int(d)).isoformat()
        except ValueError:
            return ''
    return ''


def _age_from_dob(dob):
    """Tính tuổi (số nguyên) từ chuỗi ngày sinh YYYY-MM-DD. Trả về None nếu không xác định."""
    if not dob:
        return None
    try:
        b = datetime.strptime(dob[:10], '%Y-%m-%d').date()
    except ValueError:
        return None
    t = date.today()
    return t.year - b.year - ((t.month, t.day) < (b.month, b.day))


def _age_group(age):
    """Phân nhóm độ tuổi để theo dõi doanh thu từng phân khúc."""
    if age is None:
        return 'Chưa rõ tuổi'
    if age <= 5:
        return 'Mầm non (≤5)'
    if age <= 10:
        return 'Tiểu học (6-10)'
    if age <= 15:
        return 'THCS (11-15)'
    return 'THPT+ (16+)'


@app.route('/lop-hoc/them', methods=['GET', 'POST'])
@roles_required('admin', 'director', 'manager')
def class_create():
    db = get_db()
    if request.method == 'POST':
        db.execute('''INSERT INTO classes (name, level, schedule, room, manager_id, teacher_id, note, created_at)
            VALUES (?,?,?,?,?,?,?,?)''',
            (request.form.get('name'), request.form.get('level'), _build_schedule(),
             request.form.get('room'), request.form.get('manager_id') or None,
             request.form.get('teacher_id') or None, request.form.get('note'), datetime.now().isoformat()))
        db.commit()
        flash('Đã tạo lớp học.', 'success')
        return redirect(url_for('classes_list'))
    managers = db.execute("SELECT id, full_name FROM users WHERE role IN ('manager','director','admin') AND active=1").fetchall()
    teachers = db.execute("SELECT id, full_name FROM users WHERE role='teacher' AND active=1").fetchall()
    return render_template('class_form.html', cls=None, managers=managers, teachers=teachers)


@app.route('/lop-hoc/<int:cid>/sua', methods=['GET', 'POST'])
@login_required
def class_edit(cid):
    db = get_db()
    cls = db.execute('SELECT * FROM classes WHERE id=?', (cid,)).fetchone()
    if not cls:
        abort(404)
    if not can_manage_class(cid):
        abort(403)
    if request.method == 'POST':
        db.execute('''UPDATE classes SET name=?, level=?, schedule=?, room=?, manager_id=?, teacher_id=?, note=?, active=? WHERE id=?''',
            (request.form.get('name'), request.form.get('level'), _build_schedule(),
             request.form.get('room'), request.form.get('manager_id') or None,
             request.form.get('teacher_id') or None, request.form.get('note'),
             1 if request.form.get('active') else 0, cid))
        db.commit()
        flash('Đã cập nhật lớp học.', 'success')
        return redirect(url_for('class_detail', cid=cid))
    managers = db.execute("SELECT id, full_name FROM users WHERE role IN ('manager','director','admin') AND active=1").fetchall()
    teachers = db.execute("SELECT id, full_name FROM users WHERE role='teacher' AND active=1").fetchall()
    return render_template('class_form.html', cls=cls, managers=managers, teachers=teachers)


@app.route('/lop-hoc/<int:cid>')
@login_required
def class_detail(cid):
    db = get_db()
    cls = db.execute('''SELECT c.*, u.full_name teacher_name, m.full_name manager_name
        FROM classes c LEFT JOIN users u ON u.id=c.teacher_id
        LEFT JOIN users m ON m.id=c.manager_id WHERE c.id=?''', (cid,)).fetchone()
    if not cls:
        abort(404)
    if not can_view_class(cid):
        abort(403)
    students = db.execute('SELECT * FROM students WHERE class_id=? AND active=1 ORDER BY full_name', (cid,)).fetchall()
    assignments = db.execute('SELECT * FROM assignments WHERE class_id=? ORDER BY due_date DESC', (cid,)).fetchall()
    return render_template('class_detail.html', cls=cls, students=students,
                           assignments=assignments, can_manage=can_manage_class(cid))


# ============================================================
#  HỌC SINH
# ============================================================
@app.route('/hoc-sinh')
@roles_required('admin', 'director', 'manager', 'teacher', 'parent')
def students_list():
    db = get_db()
    sids = visible_student_ids()
    if not sids:
        return render_template('students_list.html', students=[])
    class_filter = request.args.get('class_id', '')
    q = '''SELECT s.*, c.name class_name, p.full_name parent_name, p.phone parent_phone FROM students s
        LEFT JOIN classes c ON c.id=s.class_id
        LEFT JOIN users p ON p.id=s.parent_id
        WHERE s.id IN (%s)''' % ','.join('?' * len(sids))
    params = list(sids)
    if class_filter:
        q += ' AND s.class_id=?'
        params.append(class_filter)
    q += ' ORDER BY s.full_name'
    rows = db.execute(q, params).fetchall()
    classes = db.execute('SELECT id, name FROM classes WHERE active=1 ORDER BY name').fetchall()
    teachers = db.execute("SELECT id, full_name FROM users WHERE role='teacher' AND active=1 ORDER BY full_name").fetchall()
    return render_template('students_list.html', students=rows, classes=classes,
                           class_filter=class_filter, teachers=teachers)


@app.route('/hoc-sinh/in')
@roles_required('admin', 'director', 'manager', 'teacher')
def students_print():
    """In danh sách học sinh: toàn bộ / theo lớp / theo giáo viên."""
    db = get_db()
    scope = request.args.get('scope', 'all')
    sids = visible_student_ids()
    if not sids:
        return render_template('students_print.html', students=[], scope=scope, subtitle='Danh sách trống')
    base = '''SELECT s.*, c.name class_name, t.full_name teacher_name,
        p.full_name parent_name, p.phone parent_phone FROM students s
        LEFT JOIN classes c ON c.id=s.class_id
        LEFT JOIN users t ON t.id=c.teacher_id
        LEFT JOIN users p ON p.id=s.parent_id
        WHERE s.active=1 AND s.id IN (%s)''' % ','.join('?' * len(sids))
    params = list(sids)
    subtitle = 'Toàn bộ học sinh'
    if scope == 'class':
        cid = request.args.get('id', type=int)
        base += ' AND s.class_id=?'
        params.append(cid)
        c = db.execute('SELECT name FROM classes WHERE id=?', (cid,)).fetchone()
        subtitle = 'Lớp: ' + (c['name'] if c else '—')
    elif scope == 'teacher':
        tid = request.args.get('id', type=int)
        base += ' AND c.teacher_id=?'
        params.append(tid)
        t = db.execute('SELECT full_name FROM users WHERE id=?', (tid,)).fetchone()
        subtitle = 'Giáo viên: ' + (t['full_name'] if t else '—')
    base += ' ORDER BY c.name, s.full_name'
    rows = db.execute(base, params).fetchall()
    return render_template('students_print.html', students=rows, scope=scope, subtitle=subtitle)


@app.route('/hoc-sinh/them', methods=['GET', 'POST'])
@roles_required('admin', 'director', 'manager', 'teacher')
def student_create():
    db = get_db()
    if request.method == 'POST':
        cur = db.execute('''INSERT INTO students
            (code, full_name, dob, gender, phone, address, class_id, parent_id, student_user_id, monthly_fee, note, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
            (request.form.get('code'), request.form.get('full_name'), _build_dob(),
             request.form.get('gender'), request.form.get('phone'), request.form.get('address'),
             request.form.get('class_id') or None, None,
             request.form.get('student_user_id') or None,
             float(request.form.get('monthly_fee') or 0), request.form.get('note'),
             datetime.now().isoformat()))
        sid = cur.lastrowid
        pids = [request.form.get('parent_id_1') or None, request.form.get('parent_id_2') or None]
        ok, err = set_student_parents(sid, pids)
        db.commit()
        if not ok:
            flash('Đã thêm học sinh nhưng chưa gắn phụ huynh: ' + err, 'danger')
        else:
            flash('Đã thêm học sinh.', 'success')
        return redirect(url_for('students_list'))
    return render_template('student_form.html', student=None, student_parent_ids=[], **_student_form_options())


@app.route('/hoc-sinh/<int:sid>/sua', methods=['GET', 'POST'])
@roles_required('admin', 'director', 'manager', 'teacher')
def student_edit(sid):
    db = get_db()
    student = db.execute('SELECT * FROM students WHERE id=?', (sid,)).fetchone()
    if not student:
        abort(404)
    if sid not in visible_student_ids():
        abort(403)
    if request.method == 'POST':
        db.execute('''UPDATE students SET code=?, full_name=?, dob=?, gender=?, phone=?, address=?,
            class_id=?, student_user_id=?, monthly_fee=?, note=?, active=? WHERE id=?''',
            (request.form.get('code'), request.form.get('full_name'), _build_dob(),
             request.form.get('gender'), request.form.get('phone'), request.form.get('address'),
             request.form.get('class_id') or None,
             request.form.get('student_user_id') or None, float(request.form.get('monthly_fee') or 0),
             request.form.get('note'), 1 if request.form.get('active') else 0, sid))
        pids = [request.form.get('parent_id_1') or None, request.form.get('parent_id_2') or None]
        ok, err = set_student_parents(sid, pids)
        db.commit()
        if not ok:
            flash('Đã lưu hồ sơ nhưng phần phụ huynh: ' + err, 'danger')
        else:
            flash('Đã cập nhật học sinh.', 'success')
        return redirect(url_for('student_detail', sid=sid))
    return render_template('student_form.html', student=student,
                           student_parent_ids=parent_ids_of_student(sid), **_student_form_options())


def _student_form_options():
    db = get_db()
    return dict(
        classes=db.execute('SELECT id, name FROM classes WHERE active=1 ORDER BY name').fetchall(),
        parents=db.execute("SELECT id, full_name, username FROM users WHERE role='parent' AND active=1 ORDER BY full_name").fetchall(),
        student_users=db.execute("SELECT id, full_name, username FROM users WHERE role='student' AND active=1 ORDER BY full_name").fetchall(),
    )


@app.route('/hoc-sinh/<int:sid>')
@login_required
def student_detail(sid):
    db = get_db()
    if current_user.role == 'student':
        abort(403)
    if sid not in visible_student_ids():
        abort(403)
    student = db.execute('''SELECT s.*, c.name class_name, p.full_name parent_name, p.phone parent_phone
        FROM students s LEFT JOIN classes c ON c.id=s.class_id
        LEFT JOIN users p ON p.id=s.parent_id WHERE s.id=?''', (sid,)).fetchone()
    if not student:
        abort(404)
    attendance = db.execute('SELECT * FROM attendance WHERE student_id=? ORDER BY date DESC LIMIT 30', (sid,)).fetchall()
    tuition = db.execute('SELECT * FROM tuition WHERE student_id=? ORDER BY period DESC', (sid,)).fetchall()
    submissions = db.execute('''SELECT sub.*, a.title FROM submissions sub
        JOIN assignments a ON a.id=sub.assignment_id WHERE sub.student_id=? ORDER BY sub.submitted_at DESC''', (sid,)).fetchall()
    return render_template('student_detail.html', student=student, attendance=attendance,
                           tuition=tuition, submissions=submissions, parents=parents_of_student(sid))


# ============================================================
#  BÀI TẬP
# ============================================================
@app.route('/bai-tap')
@roles_required('admin', 'director', 'manager', 'teacher', 'student')
def assignments_list():
    db = get_db()
    role = current_user.role
    if role == 'student':
        srow = get_student_record_for_user()
        if not srow or not srow['class_id']:
            return render_template('assignments_list.html', assignments=[])
        rows = db.execute('''SELECT a.*, c.name class_name, sub.status sub_status, sub.score
            FROM assignments a JOIN classes c ON c.id=a.class_id
            LEFT JOIN submissions sub ON sub.assignment_id=a.id AND sub.student_id=?
            WHERE a.class_id=? ORDER BY a.due_date DESC''', (srow['id'], srow['class_id'])).fetchall()
        return render_template('assignments_list.html', assignments=rows)
    cids = visible_class_ids()
    if not cids:
        return render_template('assignments_list.html', assignments=[])
    q = '''SELECT a.*, c.name class_name,
        (SELECT COUNT(*) FROM students s WHERE s.class_id=a.class_id AND s.active=1) total_students,
        (SELECT COUNT(*) FROM submissions sub WHERE sub.assignment_id=a.id AND sub.status IN ('submitted','graded')) submitted_count
        FROM assignments a JOIN classes c ON c.id=a.class_id
        WHERE a.class_id IN (%s) ORDER BY a.due_date DESC''' % ','.join('?' * len(cids))
    rows = db.execute(q, cids).fetchall()
    return render_template('assignments_list.html', assignments=rows)


@app.route('/bai-tap/them', methods=['GET', 'POST'])
@roles_required('admin', 'director', 'manager', 'teacher')
def assignment_create():
    db = get_db()
    if request.method == 'POST':
        cid = int(request.form.get('class_id'))
        if not can_manage_class(cid):
            abort(403)
        cur = db.execute('''INSERT INTO assignments (class_id, teacher_id, title, description, due_date, created_at)
            VALUES (?,?,?,?,?,?)''',
            (cid, current_user.id, request.form.get('title'), request.form.get('description'),
             request.form.get('due_date'), datetime.now().isoformat()))
        aid = cur.lastrowid
        # Lưu ảnh trang sách / tài liệu đính kèm (nhiều file)
        files = request.files.getlist('photos') + request.files.getlist('files')
        n = 0
        for f in files:
            if f and f.filename and allowed_file(f.filename):
                fname = secure_filename(f.filename)
                stored = f"{aid}_{n}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{fname}"
                f.save(os.path.join(ASSIGNMENT_FILE_DIR, stored))
                db.execute('''INSERT INTO assignment_files (assignment_id, file_path, file_name, created_at)
                    VALUES (?,?,?,?)''', (aid, stored, fname, datetime.now().isoformat()))
                n += 1
        db.commit()
        flash('Đã giao bài tập.', 'success')
        return redirect(url_for('assignment_detail', aid=aid))
    cids = visible_class_ids()
    classes = []
    if cids:
        q = 'SELECT id, name FROM classes WHERE id IN (%s) ORDER BY name' % ','.join('?' * len(cids))
        classes = db.execute(q, cids).fetchall()
    return render_template('assignment_form.html', classes=classes)


@app.route('/bai-tap/<int:aid>')
@login_required
def assignment_detail(aid):
    db = get_db()
    a = db.execute('''SELECT a.*, c.name class_name FROM assignments a
        JOIN classes c ON c.id=a.class_id WHERE a.id=?''', (aid,)).fetchone()
    if not a:
        abort(404)
    if current_user.role == 'parent':
        abort(403)
    if not can_view_class(a['class_id']):
        abort(403)
    files = db.execute('SELECT * FROM assignment_files WHERE assignment_id=? ORDER BY id', (aid,)).fetchall()
    # Học sinh xem bài của mình + form nộp
    if current_user.role == 'student':
        srow = get_student_record_for_user()
        sub = None
        if srow:
            sub = db.execute('SELECT * FROM submissions WHERE assignment_id=? AND student_id=?',
                             (aid, srow['id'])).fetchone()
        return render_template('assignment_detail.html', a=a, my_submission=sub, submissions=None, files=files)
    # Giáo viên/quản lý: danh sách nộp của cả lớp
    submissions = db.execute('''SELECT s.id student_id, s.full_name,
        sub.id sub_id, sub.status, sub.score, sub.submitted_at, sub.file_name, sub.file_path, sub.content, sub.feedback
        FROM students s
        LEFT JOIN submissions sub ON sub.student_id=s.id AND sub.assignment_id=?
        WHERE s.class_id=? AND s.active=1 ORDER BY s.full_name''', (aid, a['class_id'])).fetchall()
    return render_template('assignment_detail.html', a=a, submissions=submissions,
                           my_submission=None, can_manage=can_manage_class(a['class_id']), files=files)


@app.route('/bai-tap/<int:aid>/nop', methods=['POST'])
@roles_required('student')
def submit_assignment(aid):
    db = get_db()
    srow = get_student_record_for_user()
    if not srow:
        abort(403)
    a = db.execute('SELECT * FROM assignments WHERE id=?', (aid,)).fetchone()
    if not a or a['class_id'] != srow['class_id']:
        abort(403)
    content = request.form.get('content', '')
    file_path = file_name = None
    f = request.files.get('file')
    if f and f.filename and allowed_file(f.filename):
        fname = secure_filename(f.filename)
        stored = f"{aid}_{srow['id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{fname}"
        f.save(os.path.join(SUBMISSION_DIR, stored))
        file_path = stored
        file_name = fname
    now = datetime.now()
    status = 'late' if a['due_date'] and now.date().isoformat() > a['due_date'] else 'submitted'
    existing = db.execute('SELECT id FROM submissions WHERE assignment_id=? AND student_id=?',
                          (aid, srow['id'])).fetchone()
    if existing:
        db.execute('''UPDATE submissions SET content=?, status=?, submitted_at=?,
            file_path=COALESCE(?, file_path), file_name=COALESCE(?, file_name) WHERE id=?''',
            (content, status, now.isoformat(), file_path, file_name, existing['id']))
    else:
        db.execute('''INSERT INTO submissions (assignment_id, student_id, content, file_path, file_name, submitted_at, status)
            VALUES (?,?,?,?,?,?,?)''',
            (aid, srow['id'], content, file_path, file_name, now.isoformat(), status))
    db.commit()
    flash('Đã nộp bài.', 'success')
    return redirect(url_for('assignment_detail', aid=aid))


@app.route('/bai-nop/<int:sub_id>/cham', methods=['POST'])
@roles_required('admin', 'director', 'manager', 'teacher')
def grade_submission(sub_id):
    db = get_db()
    sub = db.execute('''SELECT sub.*, a.class_id, a.id aid FROM submissions sub
        JOIN assignments a ON a.id=sub.assignment_id WHERE sub.id=?''', (sub_id,)).fetchone()
    if not sub:
        abort(404)
    if not can_manage_class(sub['class_id']):
        abort(403)
    score = request.form.get('score')
    db.execute('''UPDATE submissions SET score=?, feedback=?, status='graded', graded_at=? WHERE id=?''',
               (float(score) if score else None, request.form.get('feedback'),
                datetime.now().isoformat(), sub_id))
    db.commit()
    flash('Đã chấm bài.', 'success')
    return redirect(url_for('assignment_detail', aid=sub['aid']))


@app.route('/bai-nop/file/<path:filename>')
@login_required
def submission_file(filename):
    return send_from_directory(SUBMISSION_DIR, filename, as_attachment=True)


@app.route('/bai-tap/file/<path:filename>')
@login_required
def assignment_file_download(filename):
    row = get_db().execute('SELECT assignment_id FROM assignment_files WHERE file_path=?', (filename,)).fetchone()
    if not row:
        abort(404)
    a = get_db().execute('SELECT class_id FROM assignments WHERE id=?', (row['assignment_id'],)).fetchone()
    if not a or not can_view_class(a['class_id']):
        abort(403)
    return send_from_directory(ASSIGNMENT_FILE_DIR, filename, as_attachment=True)


# ============================================================
#  MINI GAME: NHÌN HÌNH ĐOÁN CHỮ
# ============================================================
@app.route('/tro-choi')
@login_required
def quiz_game():
    return render_template('quiz_game.html', questions=QUIZ_QUESTIONS)


# ---------- PWA (cài app lên điện thoại) ----------
@app.route('/manifest.json')
def pwa_manifest():
    resp = send_from_directory(app.static_folder, 'manifest.json')
    resp.headers['Content-Type'] = 'application/manifest+json'
    return resp


@app.route('/sw.js')
def pwa_service_worker():
    resp = send_from_directory(app.static_folder, 'sw.js')
    resp.headers['Content-Type'] = 'application/javascript'
    resp.headers['Service-Worker-Allowed'] = '/'
    resp.headers['Cache-Control'] = 'no-cache'
    return resp


# ============================================================
#  ĐIỂM DANH
# ============================================================
@app.route('/diem-danh', methods=['GET', 'POST'])
@roles_required('admin', 'director', 'manager', 'teacher')
def attendance_view():
    db = get_db()
    cids = visible_class_ids()
    classes = []
    if cids:
        q = 'SELECT id, name FROM classes WHERE id IN (%s) ORDER BY name' % ','.join('?' * len(cids))
        classes = db.execute(q, cids).fetchall()
    cid = request.args.get('class_id', type=int) or request.form.get('class_id', type=int)
    sel_date = request.values.get('date') or date.today().isoformat()

    if request.method == 'POST':
        if not can_manage_class(cid):
            abort(403)
        students = db.execute('SELECT id FROM students WHERE class_id=? AND active=1', (cid,)).fetchall()
        for s in students:
            status = request.form.get(f'status_{s["id"]}', 'present')
            note = request.form.get(f'note_{s["id"]}', '')
            existing = db.execute('SELECT id FROM attendance WHERE student_id=? AND date=?',
                                  (s['id'], sel_date)).fetchone()
            if existing:
                db.execute('UPDATE attendance SET status=?, note=?, class_id=? WHERE id=?',
                           (status, note, cid, existing['id']))
            else:
                db.execute('''INSERT INTO attendance (class_id, student_id, date, status, note, created_by, created_at)
                    VALUES (?,?,?,?,?,?,?)''',
                    (cid, s['id'], sel_date, status, note, current_user.id, datetime.now().isoformat()))
        db.commit()
        flash('Đã lưu điểm danh.', 'success')
        return redirect(url_for('attendance_view', class_id=cid, date=sel_date))

    students = []
    if cid and can_view_class(cid):
        students = db.execute('''SELECT s.*, att.status, att.note FROM students s
            LEFT JOIN attendance att ON att.student_id=s.id AND att.date=?
            WHERE s.class_id=? AND s.active=1 ORDER BY s.full_name''', (sel_date, cid)).fetchall()
    return render_template('attendance.html', classes=classes, students=students,
                           sel_class=cid, sel_date=sel_date)


# ============================================================
#  HỌC PHÍ
# ============================================================
@app.route('/hoc-phi')
@roles_required('admin', 'director', 'manager', 'teacher', 'parent')
def tuition_list():
    db = get_db()
    sids = visible_student_ids()
    if not sids:
        return render_template('tuition_list.html', rows=[], can_manage=False)
    period = request.args.get('period', '')
    q = '''SELECT t.*, s.full_name, c.name class_name FROM tuition t
        JOIN students s ON s.id=t.student_id
        LEFT JOIN classes c ON c.id=s.class_id
        WHERE t.student_id IN (%s)''' % ','.join('?' * len(sids))
    params = list(sids)
    if period:
        q += ' AND t.period=?'
        params.append(period)
    q += ' ORDER BY t.period DESC, s.full_name'
    rows = db.execute(q, params).fetchall()
    can_manage = has_role('admin', 'director', 'manager')
    can_approve = has_role('admin', 'director')
    pending_count = sum(1 for r in rows if not r['approved'])
    return render_template('tuition_list.html', rows=rows, period=period,
                           can_manage=can_manage, can_approve=can_approve, pending_count=pending_count)


def _month_range(p_from, p_to):
    """Danh sách các kỳ YYYY-MM từ p_from đến p_to (bao gồm 2 đầu)."""
    try:
        fy, fm = int(p_from[:4]), int(p_from[5:7])
        ty, tm = int(p_to[:4]), int(p_to[5:7])
    except (ValueError, IndexError):
        return []
    if (ty, tm) < (fy, fm):
        fy, fm, ty, tm = ty, tm, fy, fm
    out = []
    y, m = fy, fm
    while (y, m) <= (ty, tm) and len(out) <= 36:
        out.append(f'{y:04d}-{m:02d}')
        m += 1
        if m > 12:
            m = 1
            y += 1
    return out


@app.route('/hoc-phi/them', methods=['GET', 'POST'])
@roles_required('admin', 'director', 'manager')
def tuition_create():
    db = get_db()
    if request.method == 'POST':
        # Chọn 1 tháng hoặc theo kỳ (từ tháng - đến tháng)
        if request.form.get('period_mode') == 'range':
            periods = _month_range(request.form.get('period_from', ''), request.form.get('period_to', ''))
        else:
            periods = [request.form.get('period')] if request.form.get('period') else []
        target = request.form.get('target')  # 'class' hoặc 'student'
        amount_default = float(request.form.get('amount') or 0)
        due_date = request.form.get('due_date')
        if target == 'class':
            cid = int(request.form.get('class_id'))
            students = db.execute('SELECT id, monthly_fee FROM students WHERE class_id=? AND active=1', (cid,)).fetchall()
        else:
            students = db.execute('SELECT id, monthly_fee FROM students WHERE id=?',
                                  (request.form.get('student_id'),)).fetchall()
        # Giám đốc/admin tạo thì duyệt luôn; quản lý lớp tạo thì chờ giám đốc duyệt
        approved = 1 if has_role('admin', 'director') else 0
        now = datetime.now().isoformat()
        count = 0
        for period in periods:
            for s in students:
                if db.execute('SELECT 1 FROM tuition WHERE student_id=? AND period=?', (s['id'], period)).fetchone():
                    continue
                amt = amount_default if amount_default > 0 else (s['monthly_fee'] or 0)
                db.execute('''INSERT INTO tuition
                    (student_id, period, amount, paid_amount, due_date, status, created_at, created_by, approved)
                    VALUES (?,?,?,0,?,'unpaid',?,?,?)''',
                    (s['id'], period, amt, due_date, now, current_user.id, approved))
                count += 1
        db.commit()
        if approved:
            flash(f'Đã tạo {count} phiếu học phí.', 'success')
        else:
            flash(f'Đã tạo {count} phiếu học phí, đang chờ Giám đốc phê duyệt.', 'success')
        return redirect(url_for('tuition_list'))
    classes = db.execute('SELECT id, name FROM classes WHERE active=1 ORDER BY name').fetchall()
    students = db.execute('SELECT id, full_name FROM students WHERE active=1 ORDER BY full_name').fetchall()
    return render_template('tuition_form.html', classes=classes, students=students)


@app.route('/hoc-phi/<int:tid>/duyet', methods=['POST'])
@roles_required('admin', 'director')
def tuition_approve(tid):
    db = get_db()
    row = db.execute('SELECT id FROM tuition WHERE id=?', (tid,)).fetchone()
    if not row:
        abort(404)
    db.execute('UPDATE tuition SET approved=1, approved_by=?, approved_at=? WHERE id=?',
               (current_user.id, datetime.now().isoformat(), tid))
    db.commit()
    flash('Đã phê duyệt phiếu học phí.', 'success')
    return redirect(request.referrer or url_for('tuition_list'))


@app.route('/hoc-phi/duyet-tat-ca', methods=['POST'])
@roles_required('admin', 'director')
def tuition_approve_all():
    db = get_db()
    db.execute('UPDATE tuition SET approved=1, approved_by=?, approved_at=? WHERE approved=0',
               (current_user.id, datetime.now().isoformat()))
    db.commit()
    flash('Đã phê duyệt tất cả phiếu đang chờ.', 'success')
    return redirect(url_for('tuition_list'))


@app.route('/hoc-phi/<int:tid>/in')
@roles_required('admin', 'director', 'manager')
def tuition_print(tid):
    db = get_db()
    row = db.execute('''SELECT t.*, s.full_name student_name, s.code student_code, s.dob,
        c.name class_name, a.full_name approver_name FROM tuition t
        JOIN students s ON s.id=t.student_id
        LEFT JOIN classes c ON c.id=s.class_id
        LEFT JOIN users a ON a.id=t.approved_by
        WHERE t.id=?''', (tid,)).fetchone()
    if not row:
        abort(404)
    return render_template('tuition_print.html', t=row)


@app.route('/hoc-phi/<int:tid>/thu', methods=['POST'])
@roles_required('admin', 'director', 'manager')
def tuition_pay(tid):
    db = get_db()
    row = db.execute('SELECT * FROM tuition WHERE id=?', (tid,)).fetchone()
    if not row:
        abort(404)
    if not row['approved']:
        flash('Phiếu chưa được Giám đốc phê duyệt, chưa thể thu tiền.', 'danger')
        return redirect(request.referrer or url_for('tuition_list'))
    add = float(request.form.get('paid_amount') or 0)
    new_paid = (row['paid_amount'] or 0) + add
    status = recalc_tuition_status(row['amount'], new_paid)
    db.execute('UPDATE tuition SET paid_amount=?, status=? WHERE id=?', (new_paid, status, tid))
    db.commit()
    flash('Đã ghi nhận thanh toán.', 'success')
    return redirect(request.referrer or url_for('tuition_list'))


# ============================================================
#  THƯ VIỆN TÀI LIỆU
# ============================================================
@app.route('/tai-lieu')
@login_required
def documents_list():
    db = get_db()
    dids = visible_document_ids()
    if dids:
        q = '''SELECT d.*, c.name class_name, u.full_name uploader_name FROM documents d
            LEFT JOIN classes c ON c.id=d.class_id
            LEFT JOIN users u ON u.id=d.uploaded_by
            WHERE d.id IN (%s) ORDER BY d.created_at DESC''' % ','.join('?' * len(dids))
        docs = db.execute(q, dids).fetchall()
    else:
        docs = []
    can_manage = has_role('admin', 'director', 'manager', 'teacher')
    return render_template('documents_list.html', docs=docs, can_manage=can_manage)


@app.route('/tai-lieu/them', methods=['GET', 'POST'])
@roles_required('admin', 'director', 'manager', 'teacher')
def document_create():
    db = get_db()
    if request.method == 'POST':
        f = request.files.get('file')
        if not f or not f.filename:
            flash('Vui lòng chọn tệp tài liệu.', 'danger')
            return redirect(url_for('document_create'))
        if not allowed_file(f.filename):
            flash('Định dạng tệp không được hỗ trợ.', 'danger')
            return redirect(url_for('document_create'))
        cid = request.form.get('class_id') or None
        # Giáo viên/quản lý chỉ được đăng cho lớp mình phụ trách (hoặc tài liệu chung)
        if cid and not has_role('admin', 'director') and int(cid) not in visible_class_ids():
            abort(403)
        fname = secure_filename(f.filename)
        stored = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{fname}"
        f.save(os.path.join(DOC_DIR, stored))
        db.execute('''INSERT INTO documents (title, description, file_path, file_name, class_id, uploaded_by, created_at)
            VALUES (?,?,?,?,?,?,?)''',
            (request.form.get('title') or fname, request.form.get('description'),
             stored, fname, cid, current_user.id, datetime.now().isoformat()))
        db.commit()
        flash('Đã tải lên tài liệu.', 'success')
        return redirect(url_for('documents_list'))
    # Lựa chọn lớp để gắn tài liệu
    if has_role('admin', 'director'):
        classes = db.execute('SELECT id, name FROM classes WHERE active=1 ORDER BY name').fetchall()
    else:
        cids = visible_class_ids()
        classes = []
        if cids:
            q = 'SELECT id, name FROM classes WHERE id IN (%s) ORDER BY name' % ','.join('?' * len(cids))
            classes = db.execute(q, cids).fetchall()
    return render_template('document_form.html', classes=classes)


@app.route('/tai-lieu/<int:did>/xoa', methods=['POST'])
@roles_required('admin', 'director', 'manager', 'teacher')
def document_delete(did):
    db = get_db()
    doc = db.execute('SELECT * FROM documents WHERE id=?', (did,)).fetchone()
    if not doc:
        abort(404)
    # Chỉ admin/giám đốc hoặc người đăng được xóa
    if not has_role('admin', 'director') and doc['uploaded_by'] != current_user.id:
        abort(403)
    if doc['file_path']:
        try:
            os.remove(os.path.join(DOC_DIR, doc['file_path']))
        except OSError:
            pass
    db.execute('DELETE FROM documents WHERE id=?', (did,))
    db.commit()
    flash('Đã xóa tài liệu.', 'success')
    return redirect(url_for('documents_list'))


@app.route('/tai-lieu/file/<path:filename>')
@login_required
def document_file(filename):
    doc = get_db().execute('SELECT id FROM documents WHERE file_path=?', (filename,)).fetchone()
    if not doc or doc['id'] not in visible_document_ids():
        abort(403)
    return send_from_directory(DOC_DIR, filename, as_attachment=True)


# ---------- error handlers ----------
@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', code=403, msg='Bạn không có quyền truy cập trang này.'), 403


@app.errorhandler(404)
def notfound(e):
    return render_template('error.html', code=404, msg='Không tìm thấy nội dung.'), 404


@app.errorhandler(413)
def too_large(e):
    return render_template('error.html', code=413,
                           msg=f'Tệp quá lớn. Giới hạn {MAX_UPLOAD_MB}MB mỗi tệp.'), 413


init_db()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
