# Campus Event Management & Notification System

A Flask web app for posting, discovering, and registering for campus events, with notifications, search/filter, password validation, and an admin dashboard.

## Important deployment note

This is a dynamic Flask application. GitHub repository pages and GitHub Pages do not run Python, Flask routes, sessions, or SQLite. If you open the GitHub repository URL, GitHub will show this README. That is expected.

Deploy the app to a Python web host such as Render, Railway, Fly.io, PythonAnywhere, or an equivalent WSGI-capable service.

For Render, this repository includes `render.yaml`. Create a new Blueprint from the GitHub repository and Render will use:

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn wsgi:app`
- Persistent database path: `/var/data/campus.db`

## Run locally

```bash
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000

## Production start command

```bash
gunicorn wsgi:app
```

Recommended environment variables:

```bash
SECRET_KEY=replace-with-a-long-random-secret
DATABASE_PATH=/path/to/persistent/campus.db
```

If the host provides a `PORT` variable, `python app.py` will use it. WSGI hosts should use `gunicorn wsgi:app`.

## Default admin

- Email: `admin@campus.edu`
- Password: `Admin@123`

## Features

- Student signup/login with regex password validation
- Event dashboard with search and category filtering
- Event registration with reminder notifications
- Admin dashboard to post events, notify students, delete events, and view stats
- SQLite storage with automatic seed data
- Responsive Bootstrap 5 interface
