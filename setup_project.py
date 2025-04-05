import os
import shutil

# Define the project structure
project_structure = {
    "eisenhower_app": {
        "app.py": """from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "default-secret-for-dev")

login_manager = LoginManager()
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/eisenhower.db'
login_manager.init_app(app)
login_manager.login_view = "login"

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

def get_db_connection():
    conn = sqlite3.connect('instance/eisenhower.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
@login_required
def index():
    return redirect(url_for('tasks'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user_id = request.form['user_id']
        user = User(user_id)
        login_user(user)
        return redirect(url_for('tasks'))
    return render_template('login.html')

@app.route('/tasks')
@login_required
def tasks():
    conn = get_db_connection()
    tasks = conn.execute('SELECT * FROM tasks').fetchall()
    conn.close()
    return render_template('tasks.html', tasks=tasks)

@app.route('/add_task', methods=['GET', 'POST'])
@login_required
def add_task():
    if request.method == 'POST':
        title = request.form['title']
        urgency = request.form['urgency']
        importance = request.form['importance']
        conn = get_db_connection()
        conn.execute('INSERT INTO tasks (title, urgency, importance) VALUES (?, ?, ?)',
                     (title, urgency, importance))
        conn.commit()
        conn.close()
        return redirect(url_for('tasks'))
    return render_template('add_task.html')

if __name__ == '__main__':
    conn = get_db_connection()
    conn.execute('''CREATE TABLE IF NOT EXISTS tasks
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                     title TEXT NOT NULL, 
                     urgency TEXT, 
                     importance TEXT)''')
    conn.commit()
    conn.close()
    app.run(debug=True)
""",
        "requirements.txt": """flask
flask-login
python-dotenv
gunicorn
""",
        ".env": "SECRET_KEY=your-random-key-here\n",
        "instance": {
            # SQLite DB will be created by app.py, so no file needed here yet
        },
        "templates": {
            "base.html": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Eisenhower App</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="{{ url_for('static', filename='style.css') }}">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-light bg-light">
        <div class="container">
            <a class="navbar-brand" href="{{ url_for('tasks') }}">Eisenhower App</a>
            <div class="navbar-nav">
                <a class="nav-link" href="{{ url_for('add_task') }}">Add Task</a>
                <a class="nav-link" href="{{ url_for('login') }}">Login</a>
            </div>
        </div>
    </nav>
    <div class="container mt-4">
        {% block content %}{% endblock %}
    </div>
    <script src="{{ url_for('static', filename='script.js') }}"></script>
</body>
</html>
""",
            "login.html": """{% extends "base.html" %}
{% block content %}
    <h2>Login</h2>
    <form method="POST">
        <div class="mb-3">
            <label for="user_id" class="form-label">User ID</label>
            <input type="text" class="form-control" id="user_id" name="user_id" required>
        </div>
        <button type="submit" class="btn btn-primary">Login</button>
    </form>
{% endblock %}
""",
            "register.html": """{% extends "base.html" %}
{% block content %}
    <h2>Register</h2>
    <form method="POST">
        <div class="mb-3">
            <label for="user_id" class="form-label">User ID</label>
            <input type="text" class="form-control" id="user_id" name="user_id" required>
        </div>
        <button type="submit" class="btn btn-primary">Register</button>
    </form>
{% endblock %}
""",
            "tasks.html": """{% extends "base.html" %}
{% block content %}
    <h2>Your Tasks</h2>
    <div class="row">
        <div class="col-md-6">
            <h3>Urgent & Important</h3>
            <ul>
                {% for task in tasks if task.urgency == 'urgent' and task.importance == 'important' %}
                    <li>{{ task.title }}</li>
                {% endfor %}
            </ul>
        </div>
        <div class="col-md-6">
            <h3>Important, Not Urgent</h3>
            <ul>
                {% for task in tasks if task.urgency == 'not urgent' and task.importance == 'important' %}
                    <li>{{ task.title }}</li>
                {% endfor %}
            </ul>
        </div>
    </div>
    <div class="row">
        <div class="col-md-6">
            <h3>Urgent, Not Important</h3>
            <ul>
                {% for task in tasks if task.urgency == 'urgent' and task.importance == 'not important' %}
                    <li>{{ task.title }}</li>
                {% endfor %}
            </ul>
        </div>
        <div class="col-md-6">
            <h3>Not Urgent, Not Important</h3>
            <ul>
                {% for task in tasks if task.urgency == 'not urgent' and task.importance == 'not important' %}
                    <li>{{ task.title }}</li>
                {% endfor %}
            </ul>
        </div>
    </div>
{% endblock %}
""",
            "add_task.html": """{% extends "base.html" %}
{% block content %}
    <h2>Add Task</h2>
    <form method="POST">
        <div class="mb-3">
            <label for="title" class="form-label">Task Title</label>
            <input type="text" class="form-control" id="title" name="title" required>
        </div>
        <div class="mb-3">
            <label for="urgency" class="form-label">Urgency</label>
            <select class="form-select" id="urgency" name="urgency">
                <option value="urgent">Urgent</option>
                <option value="not urgent">Not Urgent</option>
            </select>
        </div>
        <div class="mb-3">
            <label for="importance" class="form-label">Importance</label>
            <select class="form-select" id="importance" name="importance">
                <option value="important">Important</option>
                <option value="not important">Not Important</option>
            </select>
        </div>
        <button type="submit" class="btn btn-primary">Add Task</button>
    </form>
{% endblock %}
""",
            "checkin.html": """{% extends "base.html" %}
{% block content %}
    <h2>Weekly Check-In</h2>
    <p>Review your tasks and adjust priorities here.</p>
    <!-- Add form or logic later -->
{% endblock %}
"""
        },
        "static": {
            "style.css": """body {
    font-family: Arial, sans-serif;
}
""",
            "script.js": """console.log("Eisenhower App loaded");
// Add interactivity later (e.g., drag-and-drop)
"""
        }
    }
}

# Function to create directories and files
def create_structure(base_path, structure):
    for name, content in structure.items():
        path = os.path.join(base_path, name)
        if isinstance(content, dict):
            # Create directory
            os.makedirs(path, exist_ok=True)
            create_structure(path, content)
        else:
            # Create file with content
            with open(path, 'w') as f:
                f.write(content.strip())

# Run the script
if __name__ == "__main__":
    base_dir = os.getcwd()
    create_structure(base_dir, project_structure)
    print("Project structure created successfully!")