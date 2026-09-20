import os
import shutil
import sqlite3
import tempfile
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Support serverless platforms like Vercel where the app directory is read-only
if os.environ.get('VERCEL'):
    DATABASE = os.path.join(tempfile.gettempdir(), 'campus.db')
    base_db = os.path.join(BASE_DIR, 'campus.db')
    if not os.path.exists(DATABASE) and os.path.exists(base_db):
        try:
            shutil.copyfile(base_db, DATABASE)
        except Exception as e:
            print(f"Failed to copy DB to temp: {e}")
else:
    DATABASE = os.path.join(BASE_DIR, 'campus.db')

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # 1. Users Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student'
        )
    ''')

    # 2. Complaints Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_id TEXT UNIQUE,
            student_name TEXT NOT NULL,
            department TEXT NOT NULL,
            building TEXT NOT NULL,
            room_no TEXT NOT NULL,
            category TEXT NOT NULL,
            problem TEXT NOT NULL,
            priority TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            date TEXT NOT NULL
        )
    ''')

    # 3. Maintenance Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS maintenance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            complaint_id TEXT UNIQUE,
            staff_name TEXT,
            repair_date TEXT,
            cost REAL DEFAULT 0,
            remarks TEXT,
            FOREIGN KEY (complaint_id) REFERENCES complaints(complaint_id)
        )
    ''')

    # 4. Applications Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_no TEXT UNIQUE NOT NULL,
            user_id INTEGER,
            student_name TEXT NOT NULL,
            dob TEXT NOT NULL,
            gender TEXT NOT NULL,
            course TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            status TEXT DEFAULT 'Under Review',
            applied_date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # 5. Admit Cards Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admit_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_number TEXT UNIQUE NOT NULL,
            app_no TEXT UNIQUE NOT NULL,
            exam_center TEXT NOT NULL,
            exam_date TEXT NOT NULL,
            reporting_time TEXT NOT NULL,
            issued_date TEXT NOT NULL,
            FOREIGN KEY (app_no) REFERENCES applications(app_no)
        )
    ''')

    # Create default accounts if empty
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        admin_pass = generate_password_hash('admin123')
        student_pass = generate_password_hash('student123')
        cursor.execute('''
            INSERT INTO users (username, email, password, role) 
            VALUES ('admin', 'admin@campus.edu', ?, 'admin')
        ''', (admin_pass,))
        cursor.execute('''
            INSERT INTO users (username, email, password, role) 
            VALUES ('rahul', 'rahul@campus.edu', ?, 'student')
        ''', (student_pass,))

    # Seed initial test records if empty
    cursor.execute("SELECT COUNT(*) FROM complaints")
    if cursor.fetchone()[0] == 0:
        sample_complaints = [
            ('CMP001', 'rahul', 'BCA', 'Block A', '204', 'Electrical', 'Fan not working', 'Medium', 'Pending', '2026-03-12'),
            ('CMP002', 'priya', 'B.Tech', 'Block B', '101', 'Furniture', 'Broken chair', 'Low', 'Resolved', '2026-04-05'),
            ('CMP003', 'rahul', 'BCA', 'Computer Lab', 'Lab 2', 'IT', 'Projector fault', 'High', 'In Progress', '2026-05-18'),
            ('CMP004', 'sneha', 'B.Sc', 'Block C', '118', 'Plumbing', 'Tap leakage', 'High', 'Resolved', '2026-06-20'),
            ('CMP005', 'rahul', 'BCA', 'Library', 'Reading Hall', 'Internet', 'Wi-Fi down', 'Medium', 'Pending', '2026-07-14'),
            ('CMP006', 'ananya', 'B.Tech', 'Hostel Block', 'H-302', 'AC/Cooling', 'AC not cooling', 'High', 'Resolved', '2026-08-10')
        ]
        cursor.executemany('''
            INSERT INTO complaints (complaint_id, student_name, department, building, room_no, category, problem, priority, status, date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', sample_complaints)

        sample_repairs = [
            ('CMP001', 'Amit Kumar', '2026-03-14', 450.0, 'Capacitor replaced'),
            ('CMP002', 'Ramesh', '2026-04-06', 150.0, 'Chair leg welded'),
            ('CMP004', 'Suresh', '2026-06-21', 650.0, 'Pipe joint fixed'),
            ('CMP006', 'Dinesh', '2026-08-12', 7800.0, 'Compressor overhaul')
        ]
        cursor.executemany('''
            INSERT INTO maintenance (complaint_id, staff_name, repair_date, cost, remarks)
            VALUES (?, ?, ?, ?, ?)
        ''', sample_repairs)

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database and all tables initialized successfully.")