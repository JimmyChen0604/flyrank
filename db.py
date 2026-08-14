import sqlite3

DB_PATH = "tasks.db"
# ---------- Database ----------
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        done BOOLEAN NOT NULL
    )
    ''')
    cur.execute('''SELECT COUNT(*) FROM tasks''')
    count = cur.fetchone()[0]
    if count == 0:
        cur.executemany(
            "INSERT INTO tasks (title, done) VALUES (?, ?)",
            [
                ("internship", False),
                ("trends tracking", False),
                ("dinner with family", False),
            ],
        )
        print("Database initialized with sample tasks.")
    else:
        print(f"Database already has {count} tasks.")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()