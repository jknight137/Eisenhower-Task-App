import unittest
import os
from app import app, get_db_connection, User  # Added User import here
from flask_login import login_user
from werkzeug.security import generate_password_hash
import psycopg2
from datetime import date, timedelta

class PriorityMasterTestCase(unittest.TestCase):
    def setUp(self):
        # Configure app for testing
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False  # Disable CSRF for testing
        self.app = app.test_client()
        
        # Use a test database
        self.db = get_db_connection()
        self.db.autocommit = True  # For simplicity in testing
        self.cur = self.db.cursor()
        
        # Drop and recreate tables
        self.cur.execute("DROP TABLE IF EXISTS tasks")
        self.cur.execute("DROP TABLE IF EXISTS users")
        self.cur.execute('''CREATE TABLE users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            password TEXT NOT NULL
        )''')
        self.cur.execute('''CREATE TABLE tasks (
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
        
        # Insert a test user
        self.test_user_id = "testuser"
        self.test_user_name = "Test User"
        self.test_user_password = "testpass"
        hashed_password = generate_password_hash(self.test_user_password)
        self.cur.execute(
            "INSERT INTO users (id, name, password) VALUES (%s, %s, %s)",
            (self.test_user_id, self.test_user_name, hashed_password)
        )

    def tearDown(self):
        # Clean up after each test
        self.cur.execute("DROP TABLE IF EXISTS tasks")
        self.cur.execute("DROP TABLE IF EXISTS users")
        self.cur.close()
        self.db.close()

    def login(self, user_id, password):
        return self.app.post('/login', data=dict(
            user_id=user_id,
            password=password
        ), follow_redirects=True)

    def test_login_success(self):
        rv = self.login(self.test_user_id, self.test_user_password)
        self.assertIn(b"Logged in successfully!", rv.data)

    def test_login_failure(self):
        rv = self.login(self.test_user_id, "wrongpass")
        self.assertIn(b"Invalid username or password.", rv.data)

    def test_add_task(self):
        with app.test_request_context():
            login_user(User(self.test_user_id, self.test_user_name, generate_password_hash(self.test_user_password)))
            rv = self.app.post('/add_task', data=dict(
                title="Test Task",
                urgency="urgent",
                importance="important",
                due_date="2025-04-10",
                impact=8,
                frequency="none"
            ), follow_redirects=True)
            self.assertIn(b"Task added successfully!", rv.data)
            self.cur.execute("SELECT * FROM tasks WHERE title = 'Test Task'")
            task = self.cur.fetchone()
            self.assertIsNotNone(task)
            self.assertEqual(task['urgency'], "urgent")

    def test_recurring_task_creation(self):
        with app.test_request_context():
            login_user(User(self.test_user_id, self.test_user_name, generate_password_hash(self.test_user_password)))
            # Add a recurring task
            self.app.post('/add_task', data=dict(
                title="Daily Test",
                urgency="not urgent",
                importance="important",
                due_date="2025-04-07",
                impact=5,
                frequency="daily"
            ), follow_redirects=True)
            # Toggle it complete
            self.cur.execute("SELECT id FROM tasks WHERE title = 'Daily Test'")
            task_id = self.cur.fetchone()['id']
            rv = self.app.get(f'/toggle_task/{task_id}', follow_redirects=True)
            self.assertIn(b"Task status updated successfully!", rv.data)
            # Check for new task
            self.cur.execute("SELECT * FROM tasks WHERE title = 'Daily Test' AND completed = FALSE")
            new_task = self.cur.fetchone()
            self.assertIsNotNone(new_task)
            self.assertEqual(new_task['due_date'], date(2025, 4, 8))  # +1 day from original

    def test_search_tasks(self):
        with app.test_request_context():
            login_user(User(self.test_user_id, self.test_user_name, generate_password_hash(self.test_user_password)))
            self.app.post('/add_task', data=dict(
                title="Searchable Task",
                urgency="urgent",
                importance="not important",
                due_date="2025-04-09",
                impact=6,
                frequency="none"
            ), follow_redirects=True)
            rv = self.app.get('/search?q=Searchable', follow_redirects=True)
            self.assertIn(b"Searchable Task", rv.data)

if __name__ == '__main__':
    # Ensure test database is used
    os.environ['DB_NAME'] = 'eisenhower_test'
    unittest.main()