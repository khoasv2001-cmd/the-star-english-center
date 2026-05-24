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
DB_PATH = os.path.join(DATA_DIR, 'data.db')

for d in (DATA_DIR, UPLOAD_DIR, SUBMISSION_DIR):
    os.makedirs(d, exist_ok=True)

ALLOWED_EXT = {'pdf', 'doc', 'docx', 'xls', 'xlsx', 'png', 'jpg', 'jpeg', 'zip', 'rar', 'txt', 'mp3', 'mp4'}
MAX_UPLOAD_MB = 50

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
    ''')
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
        has_role=has_role, today=date.today().isoformat()
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
            'SELECT DISTINCT class_id AS id FROM students WHERE parent_id=? AND class_id IS NOT NULL',
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
        rows = db.execute('SELECT id FROM students WHERE parent_id=?', (current_user.id,)).fetchall()
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
@app.route('/')
@login_required
def dashboard():
    db = get_db()
    role = current_user.role
    stats = {}

    if role in ('admin', 'director'):
        stats['total_students'] = db.execute('SELECT COUNT(*) c FROM students WHERE active=1').fetchone()['c']
        stats['total_classes'] = db.execute('SELECT COUNT(*) c FROM classes WHERE active=1').fetchone()['c']
        stats['total_teachers'] = db.execute("SELECT COUNT(*) c FROM users WHERE role='teacher' AND active=1").fetchone()['c']
        tu = db.execute("SELECT COALESCE(SUM(amount),0) a, COALESCE(SUM(paid_amount),0) p FROM tuition").fetchone()
        stats['tuition_total'] = tu['a']
        stats['tuition_paid'] = tu['p']
        stats['tuition_due'] = tu['a'] - tu['p']
        stats['classes'] = db.execute('''
            SELECT c.*, u.full_name teacher_name,
              (SELECT COUNT(*) FROM students s WHERE s.class_id=c.id AND s.active=1) student_count
            FROM classes c LEFT JOIN users u ON u.id=c.teacher_id
            WHERE c.active=1 ORDER BY c.name''').fetchall()
        return render_template('dashboard_director.html', stats=stats)

    if role in ('manager', 'teacher'):
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
            LEFT JOIN classes c ON c.id=s.class_id
            WHERE s.parent_id=? ORDER BY s.full_name''', (current_user.id,)).fetchall()
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
@app.route('/nguoi-dung')
@roles_required('admin')
def users_list():
    db = get_db()
    role_filter = request.args.get('role', '')
    if role_filter:
        rows = db.execute('SELECT * FROM users WHERE role=? ORDER BY full_name', (role_filter,)).fetchall()
    else:
        rows = db.execute('SELECT * FROM users ORDER BY role, full_name').fetchall()
    return render_template('users.html', users=rows, role_filter=role_filter)


@app.route('/nguoi-dung/them', methods=['GET', 'POST'])
@roles_required('admin')
def user_create():
    db = get_db()
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'student')
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
@login_required
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


@app.route('/lop-hoc/them', methods=['GET', 'POST'])
@roles_required('admin', 'director', 'manager')
def class_create():
    db = get_db()
    if request.method == 'POST':
        db.execute('''INSERT INTO classes (name, level, schedule, room, manager_id, teacher_id, note, created_at)
            VALUES (?,?,?,?,?,?,?,?)''',
            (request.form.get('name'), request.form.get('level'), request.form.get('schedule'),
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
            (request.form.get('name'), request.form.get('level'), request.form.get('schedule'),
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
@login_required
def students_list():
    db = get_db()
    sids = visible_student_ids()
    if not sids:
        return render_template('students_list.html', students=[])
    class_filter = request.args.get('class_id', '')
    q = '''SELECT s.*, c.name class_name, p.full_name parent_name FROM students s
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
    return render_template('students_list.html', students=rows, classes=classes, class_filter=class_filter)


@app.route('/hoc-sinh/them', methods=['GET', 'POST'])
@roles_required('admin', 'director', 'manager', 'teacher')
def student_create():
    db = get_db()
    if request.method == 'POST':
        db.execute('''INSERT INTO students
            (code, full_name, dob, gender, phone, address, class_id, parent_id, student_user_id, monthly_fee, note, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
            (request.form.get('code'), request.form.get('full_name'), request.form.get('dob'),
             request.form.get('gender'), request.form.get('phone'), request.form.get('address'),
             request.form.get('class_id') or None, request.form.get('parent_id') or None,
             request.form.get('student_user_id') or None,
             float(request.form.get('monthly_fee') or 0), request.form.get('note'),
             datetime.now().isoformat()))
        db.commit()
        flash('Đã thêm học sinh.', 'success')
        return redirect(url_for('students_list'))
    return render_template('student_form.html', student=None, **_student_form_options())


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
            class_id=?, parent_id=?, student_user_id=?, monthly_fee=?, note=?, active=? WHERE id=?''',
            (request.form.get('code'), request.form.get('full_name'), request.form.get('dob'),
             request.form.get('gender'), request.form.get('phone'), request.form.get('address'),
             request.form.get('class_id') or None, request.form.get('parent_id') or None,
             request.form.get('student_user_id') or None, float(request.form.get('monthly_fee') or 0),
             request.form.get('note'), 1 if request.form.get('active') else 0, sid))
        db.commit()
        flash('Đã cập nhật học sinh.', 'success')
        return redirect(url_for('student_detail', sid=sid))
    return render_template('student_form.html', student=student, **_student_form_options())


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
                           tuition=tuition, submissions=submissions)


# ============================================================
#  BÀI TẬP
# ============================================================
@app.route('/bai-tap')
@login_required
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
        db.execute('''INSERT INTO assignments (class_id, teacher_id, title, description, due_date, created_at)
            VALUES (?,?,?,?,?,?)''',
            (cid, current_user.id, request.form.get('title'), request.form.get('description'),
             request.form.get('due_date'), datetime.now().isoformat()))
        db.commit()
        flash('Đã giao bài tập.', 'success')
        return redirect(url_for('assignments_list'))
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
    if not can_view_class(a['class_id']):
        abort(403)
    # Học sinh xem bài của mình + form nộp
    if current_user.role == 'student':
        srow = get_student_record_for_user()
        sub = None
        if srow:
            sub = db.execute('SELECT * FROM submissions WHERE assignment_id=? AND student_id=?',
                             (aid, srow['id'])).fetchone()
        return render_template('assignment_detail.html', a=a, my_submission=sub, submissions=None)
    # Giáo viên/quản lý: danh sách nộp của cả lớp
    submissions = db.execute('''SELECT s.id student_id, s.full_name,
        sub.id sub_id, sub.status, sub.score, sub.submitted_at, sub.file_name, sub.file_path, sub.content, sub.feedback
        FROM students s
        LEFT JOIN submissions sub ON sub.student_id=s.id AND sub.assignment_id=?
        WHERE s.class_id=? AND s.active=1 ORDER BY s.full_name''', (aid, a['class_id'])).fetchall()
    return render_template('assignment_detail.html', a=a, submissions=submissions,
                           my_submission=None, can_manage=can_manage_class(a['class_id']))


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
@login_required
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
    return render_template('tuition_list.html', rows=rows, period=period, can_manage=can_manage)


@app.route('/hoc-phi/them', methods=['GET', 'POST'])
@roles_required('admin', 'director', 'manager')
def tuition_create():
    db = get_db()
    if request.method == 'POST':
        period = request.form.get('period')
        target = request.form.get('target')  # 'class' hoặc 'student'
        amount_default = float(request.form.get('amount') or 0)
        due_date = request.form.get('due_date')
        if target == 'class':
            cid = int(request.form.get('class_id'))
            students = db.execute('SELECT id, monthly_fee FROM students WHERE class_id=? AND active=1', (cid,)).fetchall()
        else:
            students = db.execute('SELECT id, monthly_fee FROM students WHERE id=?',
                                  (request.form.get('student_id'),)).fetchall()
        count = 0
        for s in students:
            if db.execute('SELECT 1 FROM tuition WHERE student_id=? AND period=?', (s['id'], period)).fetchone():
                continue
            amt = amount_default if amount_default > 0 else (s['monthly_fee'] or 0)
            db.execute('''INSERT INTO tuition (student_id, period, amount, paid_amount, due_date, status, created_at)
                VALUES (?,?,?,0,?,'unpaid',?)''', (s['id'], period, amt, due_date, datetime.now().isoformat()))
            count += 1
        db.commit()
        flash(f'Đã tạo {count} phiếu học phí cho kỳ {period}.', 'success')
        return redirect(url_for('tuition_list', period=period))
    classes = db.execute('SELECT id, name FROM classes WHERE active=1 ORDER BY name').fetchall()
    students = db.execute('SELECT id, full_name FROM students WHERE active=1 ORDER BY full_name').fetchall()
    return render_template('tuition_form.html', classes=classes, students=students)


@app.route('/hoc-phi/<int:tid>/thu', methods=['POST'])
@roles_required('admin', 'director', 'manager')
def tuition_pay(tid):
    db = get_db()
    row = db.execute('SELECT * FROM tuition WHERE id=?', (tid,)).fetchone()
    if not row:
        abort(404)
    add = float(request.form.get('paid_amount') or 0)
    new_paid = (row['paid_amount'] or 0) + add
    status = recalc_tuition_status(row['amount'], new_paid)
    db.execute('UPDATE tuition SET paid_amount=?, status=? WHERE id=?', (new_paid, status, tid))
    db.commit()
    flash('Đã ghi nhận thanh toán.', 'success')
    return redirect(request.referrer or url_for('tuition_list'))


# ---------- error handlers ----------
@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', code=403, msg='Bạn không có quyền truy cập trang này.'), 403


@app.errorhandler(404)
def notfound(e):
    return render_template('error.html', code=404, msg='Không tìm thấy nội dung.'), 404


init_db()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
