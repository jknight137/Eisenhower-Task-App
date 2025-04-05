Eisenhower Matrix Task Manager

A web application for prioritizing tasks using the Eisenhower Matrix, built with Flask, PostgreSQL, and Bootstrap.
🧠 What Is the Eisenhower Matrix?

The Eisenhower Matrix helps you categorize tasks based on urgency and importance, dividing them into four quadrants:

    Urgent & Important – Do it now
    Not Urgent & Important – Plan it
    Urgent & Not Important – Delegate it
    Not Urgent & Not Important – Eliminate it

This app provides a visual matrix, letting you create and manage tasks based on this system.
🚀 Features

    🧑‍💻 User authentication with Flask-Login
    ✅ Task creation with urgency, importance, category, and optional due date
    📆 Weekly check-in page to review and realign your priorities
    🔲 Dynamic 2x2 Eisenhower Matrix display
    💡 Clean Bootstrap 5 UI (via CDN)
    🛢️ SQLite by default (PostgreSQL supported)
    🔐 .env support via python-dotenv

🛠️ Tech Stack

    Backend: Python 3.10, Flask
    Database: SQLite (default), PostgreSQL (optional)
    Frontend: HTML, Bootstrap 5, Vanilla JS
    Deployment-ready for: Heroku (via Gunicorn)

📦 Setup Instructions

    Clone the repo

    git clone https://github.com/yourusername/eisenhower-matrix-app.git
    cd eisenhower-matrix-app

    Create a virtual environment

    python -m venv env

        On macOS/Linux:

        source env/bin/activate

        On Windows:

        env\Scripts\activate

    Install dependencies

    pip install -r requirements.txt

    Create your .env file

    Create a file named .env in the root of the project and add:

    SECRET_KEY=your-secret-key
    DATABASE_URL=sqlite:///instance/eisenhower.db

    Run the app

    python app.py

    Open the app in your browser

    Navigate to:

    http://localhost:5000

📂 Project Structure

eisenhower_app/
├── app.py
├── requirements.txt
├── .env
├── instance/
│   └── eisenhower.db
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── register.html
│   ├── tasks.html
│   ├── add_task.html
│   └── checkin.html
└── static/
    ├── style.css
    └── script.js

🌐 Deployment (Heroku)

    Add a Procfile:

    web: gunicorn app:app

    Push to Heroku and set your SECRET_KEY and DATABASE_URL as config vars.

🤝 Contributing

Pull requests welcome! For major changes, please open an issue first to discuss what you’d like to change.
🛡️ License

MIT
