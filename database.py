import sqlite3

connection = sqlite3.connect("expenses.db")
cursor = connection.cursor()


# =========================
# USERS TABLE
# =========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL
)
""")


# =========================
# CHECK EXPENSES TABLE
# =========================

cursor.execute("""
PRAGMA table_info(expenses)
""")

columns = cursor.fetchall()

column_names = [column[1] for column in columns]


# Add user_id if it doesn't exist

if "user_id" not in column_names:

    cursor.execute("""
    ALTER TABLE expenses
    ADD COLUMN user_id INTEGER
    """)

    print("user_id column added successfully.")

else:

    print("user_id column already exists.")


# =========================
# BUDGET TABLE
# =========================

cursor.execute("""
CREATE TABLE IF NOT EXISTS budget (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    amount REAL NOT NULL
)
""")


connection.commit()
connection.close()


print("Database update completed successfully!")