### TESTING CONNECTION WITH thetamind.db

import sqlite3

conn = sqlite3.connect('thetamind.db')
cursor = conn.cursor()

cursor.execute("SELECT * FROM users")
users = cursor.fetchall()

print(users)

### INSERT USERS INSERT INTO users (username, email, hashed_password) VALUES (?, ?, ?)

# conn.execute("INSERT INTO users (username, email, hashed_password) VALUES (?, ?, ?)", ("test", "test", "test"))
# conn.commit()

conn.close()
