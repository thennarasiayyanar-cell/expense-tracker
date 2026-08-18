import sqlite3

connection = sqlite3.connect("expenses.db")
cursor = connection.cursor()

# Drop existing tables (optional - only if you want to start fresh)
cursor.execute("DROP TABLE IF EXISTS expenses")
cursor.execute("DROP TABLE IF EXISTS budget")
cursor.execute("DROP TABLE IF EXISTS users")

# Create users table
cursor.execute(
    """
    CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
    """
)

# Create expenses table
cursor.execute(
    """
    CREATE TABLE expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        expense_name TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        date TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """
)

# Create budget table
cursor.execute(
    """
    CREATE TABLE budget (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        amount REAL NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """
)

connection.commit()
connection.close()

print("✅ Database initialized successfully!")