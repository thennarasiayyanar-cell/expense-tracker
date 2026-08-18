import sqlite3

conn = sqlite3.connect('expenses.db')
c = conn.cursor()

# Create a test user
c.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('testuser', 'password123'))
user_id = c.lastrowid
c.execute("INSERT INTO budgets (user_id, budget) VALUES (?, ?)", (user_id, 0))

conn.commit()
conn.close()

print("✅ Test user created: testuser / password123")
