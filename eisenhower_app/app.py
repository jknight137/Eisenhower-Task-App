from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_apscheduler import APScheduler
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, date, timedelta
from pywebpush import webpush
import json

# Initialize Flask app
load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "default-secret-for-dev")

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# User model
class User(UserMixin):
    def __init__(self, id, name, password):
        self.id = id
        self.name = name
        self.password = password

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

# Database connection
def get_db_connection():
    if 'DATABASE_URL' in os.environ:
        conn = psycopg2.connect(os.environ['DATABASE_URL'], cursor_factory=RealDictCursor)
    else:
        conn = psycopg2.connect(
            dbname=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            host=os.getenv("DB_HOST"),
            port=os.getenv("DB_PORT", "5432"),
            cursor_factory=RealDictCursor
        )
    return conn

# Custom Jinja2 filter for datetime formatting
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d'):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return value.strftime(format)

# Routes
@app.route('/')
@login_required
def index():
    return redirect(url_for('tasks'))
from pywebpush import webpush
import json

@app.route('/subscribe', methods=['POST'])
@login_required
def subscribe():
    subscription = request.get_json()
    # Store subscription in DB (e.g., new table 'subscriptions')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO subscriptions (user_id, subscription) VALUES (%s, %s)',
        (current_user.id, json.dumps(subscription))
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/send_notification', methods=['POST'])
@login_required
def send_notification():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT subscription FROM subscriptions WHERE user_id = %s', (current_user.id,))
    subscription = cur.fetchone()
    cur.close()
    conn.close()
    if subscription:
        webpush(
            subscription_info=json.loads(subscription['subscription']),
            data=json.dumps({"title": "Task Reminder", "body": "You have overdue tasks!"}),
            vapid_private_key="your_vapid_private_key",
            vapid_claims={"sub": "mailto:your@email.com"}
        )
    return jsonify({"status": "sent"})

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
    today = date.today()
    for task in tasks:
        impact = task.get('impact', 5)
        days_until_due = (task['due_date'] - today).days if task['due_date'] else 30
        task['priority'] = impact * (1 if task['importance'] == 'important' else 0.5) / max(days_until_due, 1)
    suggested_tasks = sorted(tasks, key=lambda x: x['priority'], reverse=True)[:int(len(tasks) * 0.2) or 1]
    cur.close()
    conn.close()
    return render_template('tasks.html', tasks=tasks, suggested_tasks=suggested_tasks, today=today)

@app.route('/add_task', methods=['GET', 'POST'])
@login_required
def add_task():
    if request.method == 'POST':
        title = request.form['title']
        urgency = request.form['urgency']
        importance = request.form['importance']
        due_date = request.form['due_date'] or None
        impact = int(request.form['impact'])
        frequency = request.form['frequency']
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO tasks (title, urgency, importance, due_date, impact, frequency, user_id) VALUES (%s, %s, %s, %s, %s, %s, %s)',
            (title, urgency, importance, due_date, impact, frequency, current_user.id)
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
        frequency = request.form['frequency']
        cur.execute(
            'UPDATE tasks SET title = %s, urgency = %s, importance = %s, due_date = %s, impact = %s, frequency = %s WHERE id = %s AND user_id = %s',
            (title, urgency, importance, due_date, impact, frequency, task_id, current_user.id)
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
    cur.execute('SELECT * FROM tasks WHERE id = %s AND user_id = %s', (task_id, current_user.id))
    task = cur.fetchone()
    if task and not task['completed'] and task['frequency'] != 'none':
        new_due_date = None
        if task['frequency'] == 'daily':
            new_due_date = task['due_date'] + timedelta(days=1) if task['due_date'] else date.today() + timedelta(days=1)
        elif task['frequency'] == 'weekly':
            new_due_date = task['due_date'] + timedelta(weeks=1) if task['due_date'] else date.today() + timedelta(weeks=1)
        elif task['frequency'] == 'monthly':
            new_due_date = task['due_date'] + timedelta(days=30) if task['due_date'] else date.today() + timedelta(days=30)
        if new_due_date:
            cur.execute(
                'INSERT INTO tasks (title, urgency, importance, due_date, impact, frequency, user_id) VALUES (%s, %s, %s, %s, %s, %s, %s)',
                (task['title'], task['urgency'], task['importance'], new_due_date, task['impact'], task['frequency'], current_user.id)
            )
    cur.execute('UPDATE tasks SET completed = NOT completed WHERE id = %s AND user_id = %s', (task_id, current_user.id))
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


# Initialize scheduler
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

# Scheduled task
@scheduler.task('interval', id='create_recurring_tasks', seconds=86400)  # Daily
def create_recurring_tasks():
    conn = get_db_connection()
    cur = conn.cursor()
    today = date.today()
    cur.execute("SELECT * FROM tasks WHERE frequency != 'none' AND completed = TRUE")
    completed_tasks = cur.fetchall()
    for task in completed_tasks:
        new_due_date = None
        if task['frequency'] == 'daily':
            new_due_date = (task['due_date'] or today) + timedelta(days=1)
        elif task['frequency'] == 'weekly':
            new_due_date = (task['due_date'] or today) + timedelta(weeks=1)
        elif task['frequency'] == 'monthly':
            new_due_date = (task['due_date'] or today) + timedelta(days=30)
        if new_due_date:
            cur.execute(
                'INSERT INTO tasks (title, urgency, importance, due_date, impact, frequency, user_id, completed) '
                'VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
                (task['title'], task['urgency'], task['importance'], new_due_date, task['impact'], task['frequency'], task['user_id'], False)
            )
    conn.commit()
    cur.close()
    conn.close()

@app.route('/search', methods=['GET'])
@login_required
def search():
    query = request.args.get('q', '')
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM tasks WHERE user_id = %s AND title ILIKE %s", (current_user.id, f'%{query}%'))
    tasks = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('search_results.html', tasks=tasks)

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
        frequency TEXT DEFAULT 'none',
        completed BOOLEAN DEFAULT FALSE,
        user_id TEXT NOT NULL REFERENCES users(id),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    cur.close()
    conn.close()
    app.run(debug=True)