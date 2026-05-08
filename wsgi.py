from app import app, init_db

# Initialize database on startup
try:
    init_db()
except Exception as e:
    print(f"Database initialization warning: {e}")


