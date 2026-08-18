from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
from datetime import datetime
from functools import wraps

app = Flask(__name__)

# Secret key for login session
app.secret_key = "expense_tracker_secret_key"

DATABASE = "expenses.db"


# =========================================
# DATABASE CONNECTION
# =========================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# =========================================
# CREATE DATABASE TABLES
# =========================================

def create_tables():

    conn = get_db()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # Expenses table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            expense_name TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Budget table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            budget REAL NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


# =========================================
# LOGIN REQUIRED
# =========================================

def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "username" not in session:
            return redirect("/login")

        return function(*args, **kwargs)

    return wrapper


# =========================================
# LOGIN
# =========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Please enter username and password.", "error")
            return render_template("login.html")

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password)
        )

        user = cursor.fetchone()
        conn.close()

        if user:
            session["username"] = username
            flash("Login successful!", "success")
            return redirect("/")

        flash("Invalid username or password.", "error")
        return render_template("login.html")

    return render_template("login.html")


# =========================================
# REGISTER
# =========================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            flash("Username and password are required.", "error")
            return render_template("register.html")

        conn = get_db()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password)
            )

            user_id = cursor.lastrowid

            cursor.execute(
                "INSERT INTO budgets (user_id, budget) VALUES (?, ?)",
                (user_id, 0)
            )

            conn.commit()
            conn.close()

            flash("Registration successful! Please login.", "success")
            return redirect("/login")

        except sqlite3.IntegrityError:
            conn.close()
            flash("Username already exists.", "error")
            return render_template("register.html")

    return render_template("register.html")


# =========================================
# LOGOUT
# =========================================

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.", "success")
    return redirect("/login")


# =========================================
# DASHBOARD
# =========================================

@app.route("/")
@login_required
def index():

    username = session["username"]
    search = request.args.get("search", "").strip()
    category_filter = request.args.get("category", "").strip()

    conn = get_db()
    cursor = conn.cursor()

    # Get user ID
    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user_result = cursor.fetchone()
    if not user_result:
        conn.close()
        return redirect("/logout")
    user_id = user_result["id"]

    # Get Expenses
    query = "SELECT id, expense_name, amount, category, date FROM expenses WHERE user_id = ?"
    parameters = [user_id]

    if search:
        query += " AND (expense_name LIKE ? OR category LIKE ?)"
        search_value = f"%{search}%"
        parameters.extend([search_value, search_value])

    if category_filter:
        query += " AND category = ?"
        parameters.append(category_filter)

    query += " ORDER BY id DESC"

    cursor.execute(query, parameters)
    expenses = cursor.fetchall()

    # Total Expense
    cursor.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE user_id = ?", (user_id,))
    total = float(cursor.fetchone()[0])

    # Expense Count
    cursor.execute("SELECT COUNT(*) FROM expenses WHERE user_id = ?", (user_id,))
    expense_count = int(cursor.fetchone()[0])

    # Average Expense
    average = total / expense_count if expense_count > 0 else 0

    # Get Budget
    cursor.execute("SELECT budget FROM budgets WHERE user_id = ?", (user_id,))
    budget_result = cursor.fetchone()
    budget = float(budget_result[0]) if budget_result else 0

    # Remaining Budget
    remaining_budget = budget - total

    # Budget Status
    if budget == 0:
        budget_status = "⚠️ Set your monthly budget."
    elif remaining_budget > 0:
        budget_status = f"✅ You have ₹{remaining_budget:.2f} remaining."
    elif remaining_budget == 0:
        budget_status = "⚠️ You have reached your budget."
    else:
        budget_status = f"🚨 You exceeded your budget by ₹{abs(remaining_budget):.2f}."

    # Category Data for Chart
    cursor.execute("SELECT category, SUM(amount) FROM expenses WHERE user_id = ? GROUP BY category", (user_id,))
    category_data = cursor.fetchall()

    conn.close()

    return render_template(
        "index.html",
        username=username,
        expenses=expenses,
        total=total,
        expense_count=expense_count,
        average=average,
        budget=budget,
        remaining_budget=remaining_budget,
        budget_status=budget_status,
        category_data=category_data,
        search=search,
        category_filter=category_filter
    )


# =========================================
# ADD EXPENSE
# =========================================

@app.route("/add", methods=["POST"])
@login_required
def add_expense():

    username = session["username"]
    expense_name = request.form.get("expense_name", "").strip()
    amount = request.form.get("amount", "").strip()
    category = request.form.get("category", "").strip()

    if not expense_name or not amount or not category:
        return redirect("/")

    try:
        amount = float(amount)
    except ValueError:
        return redirect("/")

    if amount < 0:
        return redirect("/")

    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user_result = cursor.fetchone()
    if not user_result:
        conn.close()
        return redirect("/logout")
    user_id = user_result["id"]

    cursor.execute(
        "INSERT INTO expenses (user_id, expense_name, amount, category, date) VALUES (?, ?, ?, ?, ?)",
        (user_id, expense_name, amount, category, date)
    )

    conn.commit()
    conn.close()

    return redirect("/")


# =========================================
# EDIT EXPENSE
# =========================================

@app.route("/edit/<int:expense_id>", methods=["GET", "POST"])
@login_required
def edit_expense(expense_id):

    username = session["username"]

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user_result = cursor.fetchone()
    if not user_result:
        conn.close()
        return redirect("/logout")
    user_id = user_result["id"]

    if request.method == "POST":

        expense_name = request.form.get("expense_name", "").strip()
        amount = request.form.get("amount", "").strip()
        category = request.form.get("category", "").strip()

        if not expense_name or not amount or not category:
            conn.close()
            return redirect(f"/edit/{expense_id}")

        try:
            amount = float(amount)
        except ValueError:
            conn.close()
            return redirect(f"/edit/{expense_id}")

        cursor.execute(
            "UPDATE expenses SET expense_name = ?, amount = ?, category = ? WHERE id = ? AND user_id = ?",
            (expense_name, amount, category, expense_id, user_id)
        )

        conn.commit()
        conn.close()

        return redirect("/")

    cursor.execute(
        "SELECT id, expense_name, amount, category, date FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, user_id)
    )

    expense = cursor.fetchone()
    conn.close()

    if not expense:
        return redirect("/")

    return render_template("edit.html", expense=expense)


# =========================================
# DELETE EXPENSE
# =========================================

@app.route("/delete/<int:expense_id>")
@login_required
def delete_expense(expense_id):

    username = session["username"]

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user_result = cursor.fetchone()
    if not user_result:
        conn.close()
        return redirect("/logout")
    user_id = user_result["id"]

    cursor.execute(
        "DELETE FROM expenses WHERE id = ? AND user_id = ?",
        (expense_id, user_id)
    )

    conn.commit()
    conn.close()

    return redirect("/")


# =========================================
# SET BUDGET
# =========================================

@app.route("/set-budget", methods=["POST"])
@login_required
def set_budget():

    username = session["username"]
    budget_value = request.form.get("budget", "").strip()

    try:
        budget = float(budget_value)
    except ValueError:
        return redirect("/")

    if budget < 0:
        return redirect("/")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user_result = cursor.fetchone()
    if not user_result:
        conn.close()
        return redirect("/logout")
    user_id = user_result["id"]

    cursor.execute("SELECT id FROM budgets WHERE user_id = ?", (user_id,))
    existing_budget = cursor.fetchone()

    if existing_budget:
        cursor.execute("UPDATE budgets SET budget = ? WHERE user_id = ?", (budget, user_id))
    else:
        cursor.execute("INSERT INTO budgets (user_id, budget) VALUES (?, ?)", (user_id, budget))

    conn.commit()
    conn.close()

    return redirect("/")


# =========================================
# MONTHLY REPORT
# =========================================

@app.route("/monthly-report")
@login_required
def monthly_report():

    username = session["username"]

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
    user_result = cursor.fetchone()
    if not user_result:
        conn.close()
        return redirect("/logout")
    user_id = user_result["id"]

    cursor.execute(
        "SELECT id, expense_name, amount, category, date FROM expenses WHERE user_id = ? ORDER BY date DESC",
        (user_id,)
    )
    expenses = cursor.fetchall()

    total = sum(float(expense["amount"]) for expense in expenses)
    expense_count = len(expenses)
    average = total / expense_count if expense_count > 0 else 0

    cursor.execute("SELECT budget FROM budgets WHERE user_id = ?", (user_id,))
    budget_result = cursor.fetchone()
    budget = float(budget_result["budget"]) if budget_result else 0

    remaining_budget = budget - total

    cursor.execute(
        "SELECT category, SUM(amount) AS total FROM expenses WHERE user_id = ? GROUP BY category",
        (user_id,)
    )
    category_data = cursor.fetchall()

    conn.close()

    return render_template(
        "monthly_report.html",
        username=username,
        expenses=expenses,
        total=total,
        expense_count=expense_count,
        average=average,
        budget=budget,
        remaining_budget=remaining_budget,
        category_data=category_data
    )


# =========================================
# RUN APPLICATION
# =========================================

if __name__ == "__main__":
    create_tables()
    app.run(debug=True)
