import random
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from functools import wraps
from flask import Flask, flash, jsonify, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
import pandas as pd
from database import get_db, init_db

app = Flask(__name__)
app.secret_key = 'campus_fix_secure_production_secret'
init_db()

# --- SMTP Configuration (Live Gmail Real-Time Delivery) ---
DEV_MODE = False
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
SENDER_EMAIL = "miriyalavenkey43@gmail.com"
SENDER_PASSWORD = "nbmd tpkw cxsy ormh"

def send_otp_email(receiver_email, otp_code):
    # Always print to terminal so you can verify without switching tabs
    print("\n" + "=" * 50)
    print(f" [OTP DISPATCH] Destination: {receiver_email} | Code: {otp_code}")
    print("=" * 50 + "\n")

    if DEV_MODE:
        return True

    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = receiver_email
        msg['Subject'] = f"CampusFix Verification Code: {otp_code}"

        body = (
            f"Hello,\n\n"
            f"Your CampusFix security verification code is: {otp_code}\n\n"
            f"This code is valid for 5 minutes.\n\n"
            f"Best regards,\n"
            f"CampusFix Administration Team"
        )
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=10)
        server.login(SENDER_EMAIL, SENDER_PASSWORD.replace(" ", ""))
        server.send_message(msg)
        server.quit()
        print(f"[SMTP SUCCESS] Email delivered to {receiver_email}")
        return True
    except Exception as e:
        print(f"[SMTP ERROR] Delivery failed: {e}")
        return False

# --- Access Decorators ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in first.')
            return redirect(url_for('login_password'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Admin privilege required.')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Public & Auth Routes ---
@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/login', methods=['GET', 'POST'])
def login_password():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? OR email = ?", (username, username))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('tickets'))
        else:
            flash('Invalid username/email or password.')
            return redirect(url_for('login_password'))

    return render_template('auth.html', mode='login_password')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE (username = ? OR email = ?) AND role = 'admin'", (username, username))
        admin_user = cursor.fetchone()
        conn.close()

        if admin_user and check_password_hash(admin_user['password'], password):
            session['user_id'] = admin_user['id']
            session['username'] = admin_user['username']
            session['role'] = 'admin'
            flash('Logged into Admin Console successfully.')
            return redirect(url_for('admin_console'))
        else:
            flash('Invalid admin credentials or access denied.')
            return redirect(url_for('admin_login'))

    return render_template('admin_login.html')

@app.route('/login-otp', methods=['GET', 'POST'])
def login_otp():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if not user:
            flash('No account found with this email address.')
            return redirect(url_for('login_otp'))

        otp = str(random.randint(100000, 999999))
        session['otp'] = otp
        session['otp_email'] = email
        session['otp_expiry'] = time.time() + 300

        if send_otp_email(email, otp):
            flash('A 6-digit OTP has been sent.')
            return redirect(url_for('verify_otp'))
        else:
            flash('Failed to deliver email. Check your SMTP settings.')
            return redirect(url_for('login_otp'))

    return render_template('auth.html', mode='request_otp')

@app.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if 'otp' not in session or 'otp_email' not in session:
        flash('No pending verification found. Please request a new OTP.')
        return redirect(url_for('login_otp'))

    if request.method == 'POST':
        entered_otp = request.form['otp'].strip()

        if time.time() > session.get('otp_expiry', 0):
            session.pop('otp', None)
            session.pop('otp_email', None)
            flash('OTP has expired. Please request a new one.')
            return redirect(url_for('login_otp'))

        if entered_otp == session.get('otp'):
            email = session.pop('otp_email')
            session.pop('otp', None)
            session.pop('otp_expiry', None)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            user = cursor.fetchone()
            conn.close()

            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            return redirect(url_for('tickets'))
        else:
            flash('Incorrect OTP code. Try again.')
            return redirect(url_for('verify_otp'))

    return render_template('auth.html', mode='verify_otp')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        role = request.form.get('role', 'student')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (username, email))
        if cursor.fetchone():
            flash('Username or Email is already registered.')
            conn.close()
            return redirect(url_for('signup'))
        conn.close()

        otp = str(random.randint(100000, 999999))
        session['reg_user'] = {
            'username': username,
            'email': email,
            'password': generate_password_hash(password),
            'role': role
        }
        session['reg_otp'] = otp
        session['reg_otp_expiry'] = time.time() + 300

        if send_otp_email(email, otp):
            flash(f'A verification code has been sent to {email}.')
            return redirect(url_for('verify_signup_otp'))
        else:
            flash('Failed to deliver email. Check your SMTP settings.')
            return redirect(url_for('signup'))

    return render_template('auth.html', mode='signup')

@app.route('/verify-signup-otp', methods=['GET', 'POST'])
def verify_signup_otp():
    if 'reg_user' not in session or 'reg_otp' not in session:
        flash('Session expired. Please register again.')
        return redirect(url_for('signup'))

    if request.method == 'POST':
        entered_otp = request.form['otp'].strip()

        if time.time() > session.get('reg_otp_expiry', 0):
            session.pop('reg_user', None)
            session.pop('reg_otp', None)
            session.pop('reg_otp_expiry', None)
            flash('Verification code expired. Please register again.')
            return redirect(url_for('signup'))

        if entered_otp == session.get('reg_otp'):
            user_data = session.pop('reg_user')
            session.pop('reg_otp', None)
            session.pop('reg_otp_expiry', None)

            conn = get_db()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
                (user_data['username'], user_data['email'], user_data['password'], user_data['role'])
            )
            conn.commit()
            conn.close()

            flash('Email verified and account created! You can now log in.')
            return redirect(url_for('login_password'))
        else:
            flash('Incorrect code. Please try again.')
            return redirect(url_for('verify_signup_otp'))

    return render_template('auth.html', mode='verify_signup_otp')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('dashboard'))

# --- Complaints & Maintenance Workspaces ---
@app.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    if request.method == 'POST':
        dept = request.form['department']
        building = request.form['building']
        room = request.form['room_no']
        category = request.form['category']
        priority = request.form['priority']
        problem = request.form['problem']
        student_name = session['username']
        date_today = datetime.now().strftime('%Y-%m-%d')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM complaints")
        complaint_id = f"CMP{cursor.fetchone()[0] + 1:03d}"

        cursor.execute('''
            INSERT INTO complaints (complaint_id, student_name, department, building, room_no, category, problem, priority, status, date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?)
        ''', (complaint_id, student_name, dept, building, room, category, problem, priority, date_today))
        conn.commit()
        conn.close()
        return redirect(url_for('tickets'))

    return render_template('register.html')

@app.route('/tickets')
@login_required
def tickets():
    search_query = request.args.get('search', '').strip()
    conn = get_db()
    cursor = conn.cursor()

    if session.get('role') == 'admin':
        if search_query:
            cursor.execute("SELECT * FROM complaints WHERE complaint_id LIKE ? OR student_name LIKE ? ORDER BY id DESC", 
                           (f"%{search_query}%", f"%{search_query}%"))
        else:
            cursor.execute("SELECT * FROM complaints ORDER BY id DESC")
    else:
        if search_query:
            cursor.execute("SELECT * FROM complaints WHERE student_name = ? AND complaint_id LIKE ? ORDER BY id DESC", 
                           (session['username'], f"%{search_query}%"))
        else:
            cursor.execute("SELECT * FROM complaints WHERE student_name = ? ORDER BY id DESC", (session['username'],))

    complaints = cursor.fetchall()
    conn.close()
    return render_template('tickets.html', complaints=complaints, search=search_query)

@app.route('/admin/console')
@admin_required
def admin_console():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT c.*, m.staff_name, m.cost, m.remarks, m.repair_date
        FROM complaints c
        LEFT JOIN maintenance m ON c.complaint_id = m.complaint_id
        ORDER BY CASE c.status WHEN 'Pending' THEN 1 WHEN 'In Progress' THEN 2 ELSE 3 END, c.id DESC
    ''')
    complaints = cursor.fetchall()
    conn.close()
    return render_template('admin_console.html', complaints=complaints)

@app.route('/admin/resolve/<complaint_id>', methods=['POST'])
@admin_required
def resolve_complaint(complaint_id):
    status = request.form.get('status')
    staff_name = request.form.get('staff_name', '').strip()
    cost_val = request.form.get('cost', 0)
    cost = float(cost_val) if cost_val else 0.0
    remarks = request.form.get('remarks', '').strip()
    repair_date = datetime.now().strftime('%Y-%m-%d')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("UPDATE complaints SET status = ? WHERE complaint_id = ?", (status, complaint_id))
    cursor.execute("SELECT id FROM maintenance WHERE complaint_id = ?", (complaint_id,))
    existing_record = cursor.fetchone()

    if existing_record:
        cursor.execute('''
            UPDATE maintenance 
            SET staff_name = ?, repair_date = ?, cost = ?, remarks = ?
            WHERE complaint_id = ?
        ''', (staff_name, repair_date, cost, remarks, complaint_id))
    else:
        cursor.execute('''
            INSERT INTO maintenance (complaint_id, staff_name, repair_date, cost, remarks)
            VALUES (?, ?, ?, ?, ?)
        ''', (complaint_id, staff_name, repair_date, cost, remarks))

    conn.commit()
    conn.close()

    flash(f"Ticket {complaint_id} updated successfully.")
    return redirect(url_for('admin_console'))

@app.route('/update-status/<complaint_id>', methods=['POST'])
@admin_required
def update_status(complaint_id):
    new_status = request.form.get('status')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE complaints SET status = ? WHERE complaint_id = ?", (new_status, complaint_id))
    conn.commit()
    conn.close()
    return redirect(url_for('tickets'))

# --- Reports & Analytics ---
@app.route('/reports')
@admin_required
def reports():
    return render_template('reports.html')

@app.route('/api/analytics')
@admin_required
def analytics():
    conn = get_db()
    df_complaints = pd.read_sql_query("SELECT * FROM complaints", conn)
    df_maint = pd.read_sql_query("SELECT * FROM maintenance", conn)
    conn.close()

    building_order = ['Block A', 'Block B', 'Block C', 'Computer Lab', 'Library', 'Hostel Block']
    category_order = ['Electrical', 'Furniture', 'Plumbing', 'IT', 'Internet', 'Cleaning', 'AC/Cooling', 'Other']

    # 1. Building counts
    bld_counts = df_complaints['building'].value_counts().to_dict() if not df_complaints.empty else {}
    buildings = building_order
    building_data = [bld_counts.get(b, 0) for b in buildings]

    # 2. Monthly Trend
    if not df_complaints.empty and 'date' in df_complaints:
        df_complaints['month'] = pd.to_datetime(df_complaints['date']).dt.strftime('%Y-%m')
        month_counts = df_complaints['month'].value_counts().sort_index().to_dict()
    else:
        month_counts = {}

    # 3. Cost by Category
    if not df_maint.empty and not df_complaints.empty:
        merged = pd.merge(df_complaints, df_maint, on='complaint_id')
        cost_map = merged.groupby('category')['cost'].sum().to_dict()
    else:
        cost_map = {}

    categories = category_order
    category_costs = [float(cost_map.get(c, 0.0)) for c in categories]

    return jsonify({
        'buildings': buildings,
        'building_data': building_data,
        'months': list(month_counts.keys()),
        'monthly_data': list(month_counts.values()),
        'categories': categories,
        'category_costs': category_costs
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
