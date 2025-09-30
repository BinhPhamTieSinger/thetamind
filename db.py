# db.py  (optional helper file)
import sqlite3
DB="thetamind.db"
def init():
    c=sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS sess (id INTEGER PRIMARY KEY,qtxt TEXT,ocrtxt TEXT,ai_res TEXT,ts DATETIME DEFAULT CURRENT_TIMESTAMP)")
    c.commit(); c.close()
