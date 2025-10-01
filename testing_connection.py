### TESTING CONNECTION WITH thetamind.db

import sqlite3

DB = "thetamind.db"

conn = sqlite3.connect('thetamind.db')
cursor = conn.cursor()

cursor.execute("SELECT * FROM users")
users = cursor.fetchall()

print(users)

### INSERT USERS INSERT INTO users (username, email, hashed_password) VALUES (?, ?, ?)

# conn.execute("INSERT INTO users (username, email, hashed_password) VALUES (?, ?, ?)", ("test", "test", "test"))
# conn.commit()

conn.close()


conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute("SELECT topic, difficulty, is_correct, COUNT(*) as count FROM quiz_history WHERE user_id = ? GROUP BY topic, difficulty, is_correct", (1,))
stats = cur.fetchall()
conn.close()