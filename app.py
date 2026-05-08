import os
import re
import sqlite3
from datetime import datetime
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(APP_DIR, "instance", "campus.db"))

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

# ---------- DB helpers ----------
def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'student'
    );
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        category TEXT,
        venue TEXT,
        date TEXT,
        organizer TEXT
    );
    CREATE TABLE IF NOT EXISTS registrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        event_id INTEGER NOT NULL,
        registered_at TEXT,
        UNIQUE(user_id, event_id)
    );
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        created_at TEXT,
        is_read INTEGER DEFAULT 0
    );
    """)

    # Seed admin
    c.execute("SELECT COUNT(*) FROM users WHERE role='admin'")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                  ("Admin", "admin@campus.edu", "Admin@123", "admin"))

    # Seed dummy events
    c.execute("SELECT COUNT(*) FROM events")
    if c.fetchone()[0] == 0:
        dummy = [
            ("AI & ML Workshop", "Hands-on workshop on building ML models with Python.", "Workshop", "Auditorium A", "2026-05-20 10:00", "CS Department"),
            ("Annual Cultural Fest", "Music, dance and drama performances by students.", "Cultural", "Open Grounds", "2026-05-25 17:00", "Cultural Club"),
            ("Hackathon 2026", "24-hour coding marathon with exciting prizes.", "Tech", "Lab Block B", "2026-06-02 09:00", "Coding Club"),
            ("Career Fair", "Meet 50+ recruiters from top companies.", "Career", "Main Hall", "2026-06-10 11:00", "Placement Cell"),
            ("Inter-college Sports Meet", "Cricket, football, basketball tournaments.", "Sports", "Sports Complex", "2026-06-15 08:00", "Sports Committee"),
            ("Startup Pitch Night", "Pitch your startup to angel investors.", "Business", "Seminar Hall", "2026-06-20 18:00", "E-Cell"),
        ]
        c.executemany("INSERT INTO events (title,description,category,venue,date,organizer) VALUES (?,?,?,?,?,?)", dummy)

    conn.commit()
    conn.close()

# ---------- Auth helpers ----------
PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#])[A-Za-z\d@$!%*?&#]{8,}$")
EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")

def login_required(role=None):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            if "user_id" not in session:
                flash("Please log in first.", "warning")
                return redirect(url_for("login"))
            if role and session.get("role") != role:
                flash("Access denied.", "danger")
                return redirect(url_for("dashboard"))
            return fn(*a, **kw)
        return wrapper
    return deco

# ---------- Routes ----------
@app.route("/")
def home():
    conn = get_db()
    events = conn.execute("SELECT * FROM events ORDER BY date LIMIT 3").fetchall()
    conn.close()
    return render_template("home.html", events=events)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        pwd = request.form["password"]

        if not name or not EMAIL_RE.match(email):
            flash("Enter a valid name and email.", "danger")
            return redirect(url_for("signup"))
        if not PASSWORD_RE.match(pwd):
            flash("Password must be 8+ chars with uppercase, lowercase, number, and special char.", "danger")
            return redirect(url_for("signup"))

        conn = get_db()
        try:
            conn.execute("INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
                         (name, email, pwd, "student"))
            conn.commit()
        except sqlite3.IntegrityError:
            flash("Email already registered.", "danger")
            return redirect(url_for("signup"))
        finally:
            conn.close()
        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        pwd = request.form["password"]
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=? AND password=?", (email, pwd)).fetchone()
        conn.close()
        if user:
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("admin") if user["role"] == "admin" else url_for("dashboard"))
        flash("Invalid credentials.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("home"))

@app.route("/dashboard")
@login_required()
def dashboard():
    q = request.args.get("q", "").strip()
    cat = request.args.get("category", "").strip()
    conn = get_db()
    sql = "SELECT * FROM events WHERE 1=1"
    params = []
    if q:
        sql += " AND (title LIKE ? OR description LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    if cat:
        sql += " AND category=?"
        params.append(cat)
    sql += " ORDER BY date"
    events = conn.execute(sql, params).fetchall()
    categories = [r[0] for r in conn.execute("SELECT DISTINCT category FROM events").fetchall()]
    my_regs = {r["event_id"] for r in conn.execute(
        "SELECT event_id FROM registrations WHERE user_id=?", (session["user_id"],)).fetchall()}
    notifications = conn.execute(
        "SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 10",
        (session["user_id"],)).fetchall()
    conn.close()
    return render_template("dashboard.html", events=events, categories=categories,
                           q=q, cat=cat, my_regs=my_regs, notifications=notifications)

@app.route("/event/<int:event_id>")
@login_required()
def event_detail(event_id):
    conn = get_db()
    event = conn.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
    if not event:
        conn.close()
        flash("Event not found.", "danger")
        return redirect(url_for("dashboard"))
    registered = conn.execute("SELECT 1 FROM registrations WHERE user_id=? AND event_id=?",
                              (session["user_id"], event_id)).fetchone() is not None
    conn.close()
    return render_template("event_detail.html", event=event, registered=registered)

@app.route("/register/<int:event_id>", methods=["POST"])
@login_required()
def register_event(event_id):
    conn = get_db()
    event = conn.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
    if not event:
        conn.close()
        flash("Event not found.", "danger")
        return redirect(url_for("dashboard"))
    try:
        conn.execute("INSERT INTO registrations (user_id,event_id,registered_at) VALUES (?,?,?)",
                     (session["user_id"], event_id, datetime.utcnow().isoformat()))
        conn.execute("INSERT INTO notifications (user_id,message,created_at) VALUES (?,?,?)",
                     (session["user_id"],
                      f"Reminder: You're registered for '{event['title']}' on {event['date']} at {event['venue']}.",
                      datetime.utcnow().isoformat()))
        conn.commit()
        flash(f"Registered for {event['title']}!", "success")
    except sqlite3.IntegrityError:
        flash("You're already registered for this event.", "info")
    finally:
        conn.close()
    return redirect(url_for("event_detail", event_id=event_id))

# ---------- Admin ----------
@app.route("/admin")
@login_required(role="admin")
def admin():
    conn = get_db()
    events = conn.execute("""
        SELECT e.*, (SELECT COUNT(*) FROM registrations r WHERE r.event_id=e.id) AS reg_count
        FROM events e ORDER BY date
    """).fetchall()
    stats = {
        "users": conn.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0],
        "events": conn.execute("SELECT COUNT(*) FROM events").fetchone()[0],
        "registrations": conn.execute("SELECT COUNT(*) FROM registrations").fetchone()[0],
    }
    conn.close()
    return render_template("admin.html", events=events, stats=stats)

@app.route("/admin/event/new", methods=["POST"])
@login_required(role="admin")
def admin_new_event():
    f = request.form
    conn = get_db()
    conn.execute("INSERT INTO events (title,description,category,venue,date,organizer) VALUES (?,?,?,?,?,?)",
                 (f["title"], f["description"], f["category"], f["venue"], f["date"], f["organizer"]))
    conn.commit()
    # Notify all students
    students = conn.execute("SELECT id FROM users WHERE role='student'").fetchall()
    for s in students:
        conn.execute("INSERT INTO notifications (user_id,message,created_at) VALUES (?,?,?)",
                     (s["id"], f"New event posted: {f['title']} on {f['date']}", datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
    flash("Event posted and students notified.", "success")
    return redirect(url_for("admin"))

@app.route("/admin/event/<int:event_id>/delete", methods=["POST"])
@login_required(role="admin")
def admin_delete_event(event_id):
    conn = get_db()
    conn.execute("DELETE FROM registrations WHERE event_id=?", (event_id,))
    conn.execute("DELETE FROM events WHERE id=?", (event_id,))
    conn.commit()
    conn.close()
    flash("Event deleted.", "info")
    return redirect(url_for("admin"))

@app.context_processor
def inject_globals():
    return {"current_year": datetime.utcnow().year}

@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(error):
    return render_template("500.html"), 500

init_db()

if __name__ == "__main__":
    app.run(
        debug=os.environ.get("FLASK_DEBUG") == "1",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
    )
