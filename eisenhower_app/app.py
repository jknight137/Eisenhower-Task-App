from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, date, timedelta

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "default-secret-for-dev")

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

class User(UserMixin):
    def __init__(self, id, name, password):
        self.id = id
        self.name = name
        self.password = password  # Store hashed password

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, name, password FROM users WHERE id = %s', (user_id,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    if user:
        return User(user['id'], user['name'], user['password'])
    return None

def get_db_connection():
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
        port=os.getenv("DB_PORT", "5432"),
        cursor_factory=RealDictCursor
    )
    return conn

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d'):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.strftime(format)

@app.route('/')
@login_required
def index():
    return redirect(url_for('tasks'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form['user_id']
        password = request.form['password']
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT id, name, password FROM users WHERE id = %s', (user_id,))
        user_data = cur.fetchone()
        cur.close()
        conn.close()
        if user_data and check_password_hash(user_data['password'], password):
            user = User(user_data['id'], user_data['name'], user_data['password'])
            login_user(user)
            flash("Logged in successfully!", "success")
            return redirect(url_for('tasks'))
        else:
            flash("Invalid username or password.", "danger")
            return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        user_id = request.form['user_id']
        name = request.form['name']
        password = request.form['password']
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT id FROM users WHERE id = %s', (user_id,))
        if cur.fetchone():
            flash("Username already taken!", "danger")
            cur.close()
            conn.close()
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(password)
        cur.execute(
            'INSERT INTO users (id, name, password) VALUES (%s, %s, %s)',
            (user_id, name, hashed_password)
        )
        conn.commit()
        cur.close()
        conn.close()
        flash("Registered successfully! Please log in.", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "success")
    return redirect(url_for('login'))

@app.route('/tasks')
@login_required
def tasks():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM tasks WHERE user_id = %s ORDER BY due_date ASC', (current_user.id,))
    tasks = cur.fetchall()
    for task in tasks:
        impact = task.get('impact', 5)
        days_until_due = (task['due_date'] - date.today()).days if task['due_date'] else 30
        task['priority'] = impact * (1 if task['importance'] == 'important' else 0.5) / max(days_until_due, 1)
    suggested_tasks = sorted(tasks, key=lambda x: x['priority'], reverse=True)[:int(len(tasks) * 0.2) or 1]
    cur.close()
    conn.close()
    return render_template('tasks.html', tasks=tasks, suggested_tasks=suggested_tasks, today=date.today())

@app.route('/add_task', methods=['GET', 'POST'])
@login_required
def add_task():
    if request.method == 'POST':
        title = request.form['title']
        urgency = request.form['urgency']
        importance = request.form['importance']
        due_date = request.form['due_date'] or None
        impact = int(request.form['impact'])
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO tasks (title, urgency, importance, due_date, impact, user_id) VALUES (%s, %s, %s, %s, %s, %s)',
            (title, urgency, importance, due_date, impact, current_user.id)
        )
        conn.commit()
        cur.close()
        conn.close()
        flash("Task added successfully!", "success")
        return redirect(url_for('tasks'))
    return render_template('add_task.html')

@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    conn = get_db_connection()
    cur = conn.cursor()
    if request.method == 'POST':
        title = request.form['title']
        urgency = request.form['urgency']
        importance = request.form['importance']
        due_date = request.form['due_date'] or None
        impact = int(request.form['impact'])
        cur.execute(
            'UPDATE tasks SET title = %s, urgency = %s, importance = %s, due_date = %s, impact = %s WHERE id = %s AND user_id = %s',
            (title, urgency, importance, due_date, impact, task_id, current_user.id)
        )
        conn.commit()
        cur.close()
        conn.close()
        flash("Task updated successfully!", "success")
        return redirect(url_for('tasks'))
    cur.execute('SELECT * FROM tasks WHERE id = %s AND user_id = %s', (task_id, current_user.id))
    task = cur.fetchone()
    cur.close()
    conn.close()
    if not task:
        flash("Task not found!", "danger")
        return redirect(url_for('tasks'))
    return render_template('edit_task.html', task=task)

@app.route('/delete_task/<int:task_id>')
@login_required
def delete_task(task_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('DELETE FROM tasks WHERE id = %s AND user_id = %s', (task_id, current_user.id))
    conn.commit()
    cur.close()
    conn.close()
    flash("Task deleted successfully!", "success")
    return redirect(url_for('tasks'))

@app.route('/toggle_task/<int:task_id>')
@login_required
def toggle_task(task_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'UPDATE tasks SET completed = NOT completed WHERE id = %s AND user_id = %s',
        (task_id, current_user.id)
    )
    conn.commit()
    cur.close()
    conn.close()
    flash("Task status updated successfully!", "success")
    return redirect(url_for('tasks'))

@app.route('/report')
@login_required
def report():
    conn = get_db_connection()
    cur = conn.cursor()
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    query = 'SELECT * FROM tasks WHERE user_id = %s AND completed = TRUE'
    params = [current_user.id]
    if start_date:
        query += ' AND created_at >= %s'
        params.append(start_date)
    if end_date:
        query += ' AND created_at <= %s'
        params.append(end_date)
    query += ' ORDER BY created_at DESC'
    cur.execute(query, params)
    completed_tasks = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('report.html', completed_tasks=completed_tasks)

@app.route('/checkin')
@login_required
def checkin():
    conn = get_db_connection()
    cur = conn.cursor()
    today = date.today()
    week_ago = today - timedelta(days=7)
    next_week = today + timedelta(days=7)
    cur.execute(
        'SELECT * FROM tasks WHERE user_id = %s AND completed = TRUE AND created_at >= %s ORDER BY created_at DESC',
        (current_user.id, week_ago)
    )
    completed_tasks = cur.fetchall()
    cur.execute(
        'SELECT * FROM tasks WHERE user_id = %s AND completed = FALSE AND due_date < %s',
        (current_user.id, today)
    )
    overdue_tasks = cur.fetchall()
    cur.execute(
        'SELECT * FROM tasks WHERE user_id = %s AND completed = FALSE AND due_date BETWEEN %s AND %s ORDER BY due_date ASC',
        (current_user.id, today, next_week)
    )
    upcoming_tasks = cur.fetchall()
    cur.execute('SELECT * FROM tasks WHERE user_id = %s AND completed = FALSE ORDER BY due_date ASC', (current_user.id,))
    tasks = cur.fetchall()
    for task in tasks:
        impact = task.get('impact', 5)
        days_until_due = (task['due_date'] - today).days if task['due_date'] else 30
        task['priority'] = impact * (1 if task['importance'] == 'important' else 0.5) / max(days_until_due, 1)
    suggested_tasks = sorted(tasks, key=lambda x: x['priority'], reverse=True)[:int(len(tasks) * 0.2) or 1]
    cur.close()
    conn.close()
    return render_template('checkin.html', completed_tasks=completed_tasks, overdue_tasks=overdue_tasks,
                          upcoming_tasks=upcoming_tasks, suggested_tasks=suggested_tasks, today=today)

if __name__ == '__main__':
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        password TEXT NOT NULL
    )''')
    cur.execute('''CREATE TABLE IF NOT EXISTS tasks (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        urgency TEXT NOT NULL,
        importance TEXT NOT NULL,
        due_date DATE,
        impact INTEGER DEFAULT 5,
        completed BOOLEAN DEFAULT FALSE,
        user_id TEXT NOT NULL REFERENCES users(id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    cur.close()
    conn.close()
    app.run(debug=True)