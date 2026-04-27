import sqlite3
from datetime import timedelta
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask import jsonify

app = Flask(__name__)
app.secret_key = "secret123"
app.permanent_session_lifetime = timedelta(hours=2)

DATABASE = "database.db"


def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        )
    """)

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN privacy_consent INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN consent_timestamp DATETIME")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'pending'")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'employee'")
    except sqlite3.OperationalError:
        pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            username TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp DATETIME DEFAULT (datetime('now','localtime'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS direct_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            sender TEXT NOT NULL,
            receiver TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp DATETIME DEFAULT (datetime('now','localtime'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS private_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL,
            chat_key TEXT NOT NULL,
            sender TEXT NOT NULL,
            message TEXT NOT NULL,
            timestamp DATETIME DEFAULT (datetime('now','localtime'))
        )
    """)

    conn.commit()
    conn.close()


@app.route("/")
def home():
    return render_template(
        "index.html",
        user=session.get("user"),
        company=session.get("company"),
    )

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"].strip()

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT company, password, status FROM users WHERE username = ?",
            (username,)
        )
        user = cursor.fetchone()
        conn.close()

        print("USER FOUND:", user)

        if user and check_password_hash(user[1], password):

            if user[2] != "approved":
                return render_template(
                    "login.html",
                    error="Account pending approval",
                    show_header=False
                )

            session["user"] = username
            session["company"] = user[0]
            return redirect(url_for("chat"))

        return render_template(
            "login.html",
            error="Invalid login",
            show_header=False
        )

    return render_template("login.html", show_header=False)

@app.route("/chat", methods=["GET", "POST"])
def chat():
    if "user" not in session or "company" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if request.method == "POST":
        message = request.form["message"]

        cursor.execute(
            "INSERT INTO messages (company, username, message) VALUES (?, ?, ?)",
            (session["company"], session["user"], message)
        )
        conn.commit()
        conn.close()
        return redirect(url_for("chat"))

    cursor.execute(
        """
        SELECT username, message, strftime('%d/%m/%Y %H:%M', timestamp)
        FROM messages
        WHERE company = ?
        ORDER BY id DESC
        """,
        (session["company"],)
    )

    messages = cursor.fetchall()
    conn.close()

    return render_template(
        "chat.html",
        messages=messages,
        user=session["user"],
        company=session["company"],
        show_header=True
    )


@app.route("/messages")
def get_messages():
    if "user" not in session or "company" not in session:
        return jsonify([])

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT username, message, strftime('%d/%m/%Y %H:%M', timestamp)
        FROM messages
        WHERE company = ?
        ORDER BY id DESC
        """,
        (session["company"],)
    )

    messages = cursor.fetchall()
    conn.close()

    return jsonify(messages)


@app.route("/register", methods=["GET", "POST"])
def register():
    companies = [
        "BlueWaveSecure Consulting",
        "NexaSecure Solutions",
        "UrbanNet Retail",
        "MedSecure Clinic",
        "BurgerMunch"
    ]

    if request.method == "POST":

        if "privacy" not in request.form:
            return render_template(
                "register.html",
                companies=companies,
                error="You must accept the Privacy Policy"
            )

        company = request.form["company"]
        username = request.form["username"]
        password = request.form["password"]

        hashed = generate_password_hash(password)

        # Maryam is admin, so approve automatically
        status = "approved" if username.lower() == "maryam" else "pending"

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO users (company, username, password, privacy_consent, consent_timestamp, status)
                VALUES (?, ?, ?, ?, datetime('now','localtime'), ?)
                """,
                (company, username, hashed, 1, status)
            )
            conn.commit()
            conn.close()

            if status == "approved":
                return redirect(url_for("login"))

            return render_template(
                "login.html",
                error="Account created. Please wait for admin approval before logging in."
            )

        except sqlite3.IntegrityError:
            conn.close()
            return render_template(
                "register.html",
                companies=companies,
                error="Username already exists"
            )

    return render_template("register.html", companies=companies)

@app.route("/direct")
def direct():
    if "user" not in session or "company" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT username FROM users WHERE company = ? AND username != ? AND status = 'approved'",
        (session["company"], session["user"])
    )
    users = cursor.fetchall()
    conn.close()

    return render_template(
        "direct.html",
        users=users,
        user=session["user"],
        company=session["company"],
        show_header=True
    )

@app.route("/direct/<username>", methods=["GET", "POST"])
def direct_chat(username):
    if "user" not in session or "company" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if request.method == "POST":
        message = request.form["message"]

        cursor.execute(
            "INSERT INTO direct_messages (company, sender, receiver, message) VALUES (?, ?, ?, ?)",
            (session["company"], session["user"], username, message)
        )

        conn.commit()
        conn.close()
        return redirect(url_for("direct_chat", username=username))

    cursor.execute(
        """
        SELECT sender, receiver, message, strftime('%d/%m/%Y %H:%M', timestamp)
        FROM direct_messages
        WHERE company = ?
        AND ((sender = ? AND receiver = ?) OR (sender = ? AND receiver = ?))
        ORDER BY id DESC
        """,
        (session["company"], session["user"], username, username, session["user"])
    )

    messages = cursor.fetchall()
    conn.close()

    return render_template(
        "direct_chat.html",
        target_user=username,
        messages=messages,
        user=session["user"],
        company=session["company"],
    )

@app.route("/direct_messages/<username>")
def direct_messages(username):
    if "user" not in session or "company" not in session:
        return jsonify([])

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT sender, receiver, message, strftime('%d/%m/%Y %H:%M', timestamp)
        FROM direct_messages
        WHERE company = ?
        AND ((sender = ? AND receiver = ?) OR (sender = ? AND receiver = ?))
        ORDER BY id DESC
        """,
        (session["company"], session["user"], username, username, session["user"])
    )

    messages = cursor.fetchall()
    conn.close()

    return jsonify(messages)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if "user" not in session or "company" not in session:
        return redirect(url_for("login"))

    company_admins = ["maryam", "jake", "sara", "adam", "layla"]

    if session["user"].lower() not in company_admins:
        return "Access denied. Admin only."

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if request.method == "POST":
        action = request.form["action"]

        if action == "add":
            username = request.form["username"]
            password = request.form["password"]
            hashed_password = generate_password_hash(password)

            try:
                cursor.execute(
                    """
                    INSERT INTO users (company, username, password, privacy_consent, consent_timestamp, status)
                    VALUES (?, ?, ?, ?, datetime('now','localtime'), 'approved')
                    """,
                    (session["company"], username, hashed_password, 1)
                )
                conn.commit()

            except sqlite3.IntegrityError:
                conn.close()
                return "Username already exists"

        elif action == "delete":
            username = request.form["username"]

            if username != session["user"]:
                cursor.execute(
                    "DELETE FROM users WHERE company = ? AND username = ?",
                    (session["company"], username)
                )
                conn.commit()

        elif action == "approve":
            username = request.form["username"]

            cursor.execute(
                "UPDATE users SET status = 'approved' WHERE username = ? AND company = ?",
                (username, session["company"])
            )
            conn.commit()

    cursor.execute(
        "SELECT COUNT(*) FROM users WHERE company = ? AND status = 'approved'",
        (session["company"],)
    )
    employee_count = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM messages WHERE company = ?",
        (session["company"],)
    )
    group_message_count = cursor.fetchone()[0]

    cursor.execute(
        "SELECT COUNT(*) FROM direct_messages WHERE company = ?",
        (session["company"],)
    )
    direct_message_count = cursor.fetchone()[0]

    cursor.execute(
        "SELECT username, status FROM users WHERE company = ? AND status = 'approved' ORDER BY username ASC",
        (session["company"],)
    )
    employees = cursor.fetchall()

    cursor.execute(
        "SELECT username FROM users WHERE company = ? AND status = 'pending' ORDER BY username ASC",
        (session["company"],)
    )
    pending_users = cursor.fetchall()

    conn.close()

    return render_template(
    "admin.html",
    user=session["user"],
    company=session["company"],
    employee_count=employee_count,
    group_message_count=group_message_count,
    direct_message_count=direct_message_count,
    employees=employees,
    pending_users=pending_users,
    show_header=True
)


@app.route("/private", methods=["GET", "POST"])
def private():
    if "user" not in session or "company" not in session:
        return redirect(url_for("login"))

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT username FROM users WHERE company = ? AND username != ? AND status = 'approved'",
        (session["company"], session["user"])
    )
    users = cursor.fetchall()
    conn.close()

    if request.method == "POST":
        selected_users = request.form.getlist("selected_users")

        if len(selected_users) < 2 or len(selected_users) > 3:
            return render_template(
                "private.html",
                users=users,
                user=session["user"],
                company=session["company"],
                error="Please select 2 or 3 employees."
            )

        members = selected_users + [session["user"]]
        members.sort()
        chat_key = ",".join(members)

        return redirect(url_for("private_chat", chat_key=chat_key))

    return render_template(
        "private.html",
        users=users,
        user=session["user"],
        company=session["company"],
        show_header=True
    )


@app.route("/private_chat/<chat_key>", methods=["GET", "POST"])
def private_chat(chat_key):
    if "user" not in session or "company" not in session:
        return redirect(url_for("login"))

    members = chat_key.split(",")

    if session["user"] not in members:
        return "Access denied."

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if request.method == "POST":
        message = request.form["message"]

        cursor.execute(
            """
            INSERT INTO private_messages (company, chat_key, sender, message)
            VALUES (?, ?, ?, ?)
            """,
            (session["company"], chat_key, session["user"], message)
        )
        conn.commit()
        conn.close()

        return redirect(url_for("private_chat", chat_key=chat_key))

    cursor.execute(
        """
        SELECT sender, message, strftime('%d/%m/%Y %H:%M', timestamp)
        FROM private_messages
        WHERE company = ? AND chat_key = ?
        ORDER BY id DESC
        """,
        (session["company"], chat_key)
    )
    messages = cursor.fetchall()
    conn.close()

    return render_template(
        "private_chat.html",
        members=members,
        messages=messages,
        user=session["user"],
        company=session["company"],
    )

@app.route("/private_messages/<chat_key>")
def private_messages(chat_key):
    if "user" not in session or "company" not in session:
        return jsonify([])

    members = chat_key.split(",")

    if session["user"] not in members:
        return jsonify([])

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT sender, message, strftime('%d/%m/%Y %H:%M', timestamp)
        FROM private_messages
        WHERE company = ? AND chat_key = ?
        ORDER BY id DESC
        """,
        (session["company"], chat_key)
    )

    messages = cursor.fetchall()
    conn.close()

    return jsonify(messages)


@app.route("/create_company", methods=["GET", "POST"])
def create_company():
    if request.method == "POST":
        company = request.form["company"]
        name = request.form["name"]
        email = request.form["email"]

        return render_template(
            "create_company.html",
            success="Request submitted. An administrator will review your company."
        )

    return render_template("create_company.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/pricing")
def pricing():
    return render_template("pricing.html", user=session.get("user"), company=session.get("company"))


@app.route("/about")
def about():
    return render_template("about.html", user=session.get("user"), company=session.get("company"))


@app.route("/contact")
def contact():
    return render_template("contact.html", user=session.get("user"), company=session.get("company"))


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/delete_my_data", methods=["POST"])
def delete_my_data():
    if "user" not in session or "company" not in session:
        return redirect(url_for("login"))

    username = session["user"]
    company = session["company"]

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute(
        "DELETE FROM messages WHERE company = ? AND username = ?",
        (company, username)
    )

    cursor.execute(
        "DELETE FROM direct_messages WHERE company = ? AND (sender = ? OR receiver = ?)",
        (company, username, username)
    )

    cursor.execute(
        "DELETE FROM private_messages WHERE company = ? AND sender = ?",
        (company, username)
    )

    cursor.execute(
        "DELETE FROM users WHERE company = ? AND username = ?",
        (company, username)
    )

    conn.commit()
    conn.close()

    session.clear()
    return redirect(url_for("register"))


@app.route("/account")
def account():
    if "user" not in session:
        return redirect(url_for("login"))

    return render_template("account.html", user=session["user"], company=session["company"])


@app.route("/clear_messages")
def clear_messages():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages")
    conn.commit()
    conn.close()
    return "Messages cleared. Go back to /chat"


@app.route("/approve_maryam")
def approve_maryam():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute(
        "UPDATE users SET status = 'approved' WHERE lower(username) = 'maryam'"
    )

    conn.commit()
    conn.close()

    return "Maryam approved"

@app.context_processor
def inject_user():
    return dict(user=session.get("user"), company=session.get("company"))


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
