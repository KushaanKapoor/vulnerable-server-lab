import os
import sqlite3
import subprocess
from flask import (
    Flask, request, render_template_string, redirect,
    url_for, session, flash, send_from_directory
)

app = Flask(__name__)
app.secret_key = "super-insecure-key-for-lab-only"

DB_PATH = os.path.join(os.path.dirname(__file__), "eiresec.db")
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT DEFAULT 'employee'
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS confidential_docs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            owner TEXT
        )
    """)
    seed_users = [
        ("admin",   "admin123",    "admin"),
        ("kushaan", "kush2024",    "employee"),
        ("sean",    "sean2024",    "employee"),
        ("kevin",   "kevin2024",   "employee"),
        ("ganesh",  "ganesh2024",  "employee"),
    ]
    for u, p, r in seed_users:
        try:
            c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (u, p, r))
        except sqlite3.IntegrityError:
            pass

    seed_docs = [
        ("Q4 Financial Report",   "Revenue: €4.2M | Net Profit: €1.1M | CONFIDENTIAL", "admin"),
        ("Employee Salary Sheet", "Kushaan: €62k | Sean: €58k | Kevin: €65k | Ganesh: €60k", "admin"),
        ("Client List 2025",      "Acme Corp, Globex Inc, Initech Ltd — under NDA",     "kushaan"),
        ("Server Root Password",  "root password: Tr0ub4dor&3 (DO NOT SHARE)",          "admin"),
    ]
    for t, content, owner in seed_docs:
        try:
            c.execute("INSERT INTO confidential_docs (title, content, owner) VALUES (?, ?, ?)", (t, content, owner))
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()


BASE_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=Space+Grotesk:wght@400;600;700&display=swap');
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'IBM Plex Mono', monospace;
    background: #ffffff;
    color: #111827;
    min-height: 100vh;
  }
  .navbar {
    background: #ffffff;
    border-bottom: 1px solid #d1d5db;
    padding: 1rem 2rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .navbar .brand {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.4rem;
    font-weight: 700;
    color: #60a5fa;
  }
  .navbar .brand span { color: #f97316; }
  .navbar nav a {
    color: #4b5563;
    text-decoration: none;
    margin-left: 1.5rem;
    font-size: 0.85rem;
    transition: color 0.2s;
  }
  .navbar nav a:hover { color: #1d4ed8; }
  .container { max-width: 800px; margin: 3rem auto; padding: 0 1.5rem; }
  h1 {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.8rem;
    color: #111827;
    margin-bottom: 1.5rem;
  }
  .card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 2rem;
    margin-bottom: 1.5rem;
  }
  input[type="text"], input[type="password"], input[type="file"], textarea {
    width: 100%;
    padding: 0.75rem 1rem;
    background: #ffffff;
    border: 1px solid #d1d5db;
    border-radius: 6px;
    color: #111827;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.9rem;
    margin-bottom: 1rem;
  }
  input:focus { outline: none; border-color: #1d4ed8; }
  button, .btn {
    background: #1e40af;
    color: #fff;
    border: none;
    padding: 0.7rem 1.5rem;
    border-radius: 6px;
    cursor: pointer;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.85rem;
    font-weight: 600;
    transition: background 0.2s;
    text-decoration: none;
    display: inline-block;
  }
  button:hover, .btn:hover { background: #2563eb; }
  .flash {
    background: #7f1d1d;
    border: 1px solid #dc2626;
    color: #fca5a5;
    padding: 0.75rem 1rem;
    border-radius: 6px;
    margin-bottom: 1rem;
    font-size: 0.85rem;
  }
  .flash.success {
    background: #14532d;
    border-color: #22c55e;
    color: #86efac;
  }
  table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 1rem;
  }
  th, td {
    text-align: left;
    padding: 0.6rem 0.8rem;
    border-bottom: 1px solid #e5e7eb;
    font-size: 0.85rem;
  }
  th { color: #1d4ed8; font-weight: 600; }
  pre {
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    padding: 1rem;
    overflow-x: auto;
    font-size: 0.8rem;
    color: #065f46;
    margin-top: 1rem;
    white-space: pre-wrap;
  }
  .tag {
    display: inline-block;
    font-size: 0.7rem;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    font-weight: 600;
  }
  .tag-danger { background: #fee2e2; color: #991b1b; }
  .tag-warn   { background: #fef3c7; color: #92400e; }
  .tag-info   { background: #dbeafe; color: #1e3a8a; }
  .feature-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 1rem;
    margin-top: 1.5rem;
  }
  .feature-card {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 8px;
    padding: 1.5rem;
    text-align: center;
    transition: border-color 0.2s;
  }
  .feature-card:hover { border-color: #1d4ed8; }
  .feature-card h3 {
    font-family: 'Space Grotesk', sans-serif;
    color: #111827;
    margin-bottom: 0.5rem;
    font-size: 1rem;
  }
  .feature-card p { font-size: 0.75rem; color: #4b5563; }
  .feature-card a { text-decoration: none; color: inherit; }
</style>
"""

NAVBAR = """
<div class="navbar">
  <div class="brand">Éire<span>Sec</span> Portal</div>
  <nav>
    <a href="/">Home</a>
    <a href="/netdiag">Net Diagnostics</a>
    <a href="/upload">Upload</a>
    <a href="/docs">Documents</a>
    {% if session.get('user') %}
      <a href="/logout">Logout ({{ session['user'] }})</a>
    {% else %}
      <a href="/login">Login</a>
    {% endif %}
  </nav>
</div>
"""

@app.route("/")
def index():
    return render_template_string(BASE_CSS + NAVBAR + """
    <div class="container">
      <h1>Welcome to the ÉireSec Internal Portal</h1>
      <p style="color:#6b7280; margin-bottom: 2rem;">
        Internal tools for ÉireSec employees. Please log in to access confidential resources.
      </p>
      <div class="feature-grid">
        <div class="feature-card">
          <a href="/login">
            <h3>🔐 Login</h3>
            <p>Employee authentication portal</p>
          </a>
        </div>
        <div class="feature-card">
          <a href="/netdiag">
            <h3>🌐 Net Diagnostics</h3>
            <p>Network connectivity tools</p>
          </a>
        </div>
        <div class="feature-card">
          <a href="/upload">
            <h3>📁 File Upload</h3>
            <p>Upload employee documents</p>
          </a>
        </div>
      </div>
    </div>
    """)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"

        app.logger.info(f"LOGIN ATTEMPT — query: {query}")

        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        try:
            c.execute(query)
            user = c.fetchone()
        except Exception as e:
            conn.close()
            error = f"Database error: {e}"
            return render_template_string(BASE_CSS + NAVBAR + LOGIN_PAGE, error=error)

        conn.close()

        if user:
            session["user"] = user["username"]
            session["role"] = user["role"]
            flash(f"Welcome back, {user['username']}!", "success")
            return redirect(url_for("docs"))
        else:
            error = "Invalid credentials."

    return render_template_string(BASE_CSS + NAVBAR + LOGIN_PAGE, error=error)


LOGIN_PAGE = """
<div class="container">
  <h1>Employee Login</h1>
  <div class="card">
    {% if error %}
      <div class="flash">{{ error }}</div>
    {% endif %}
    {% for msg in get_flashed_messages() %}
      <div class="flash success">{{ msg }}</div>
    {% endfor %}
    <form method="POST">
      <label style="font-size:0.8rem; color:#4b5563;">Username</label>
      <input type="text" name="username" placeholder="Enter username" autocomplete="off">
      <label style="font-size:0.8rem; color:#4b5563;">Password</label>
      <input type="password" name="password" placeholder="Enter password">
      <button type="submit">Log In</button>
    </form>
  </div>
</div>
"""


@app.route("/netdiag", methods=["GET", "POST"])
def netdiag():
    output = None
    host = ""
    if request.method == "POST":
        host = request.form.get("host", "")

        cmd = f"ping -c 2 {host}"

        app.logger.info(f"NETDIAG — executing: {cmd}")

        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=10
            )
            output = result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            output = "Command timed out."
        except Exception as e:
            output = f"Error: {e}"

    return render_template_string(BASE_CSS + NAVBAR + NETDIAG_PAGE, output=output, host=host)


NETDIAG_PAGE = """
<div class="container">
  <h1>Network Diagnostics</h1>
  <div class="card">
    <p style="font-size:0.8rem; color:#6b7280; margin-bottom:1rem;">
      Ping a host to check network connectivity.
    </p>
    <form method="POST">
      <label style="font-size:0.8rem; color:#4b5563;">Hostname or IP</label>
      <input type="text" name="host" placeholder="e.g. 8.8.8.8" value="{{ host }}" autocomplete="off">
      <button type="submit">Run Ping</button>
    </form>
    {% if output %}
      <pre>{{ output }}</pre>
    {% endif %}
  </div>
</div>
"""


@app.route("/upload", methods=["GET", "POST"])
def upload():
    message = None
    msg_type = ""
    if request.method == "POST":
        f = request.files.get("file")
        if f and f.filename:
            filepath = os.path.join(UPLOAD_FOLDER, f.filename)
            f.save(filepath)

            app.logger.info(f"FILE UPLOAD — saved: {filepath}")

            message = f"File '{f.filename}' uploaded successfully."
            msg_type = "success"
        else:
            message = "No file selected."
            msg_type = "error"

    files = os.listdir(UPLOAD_FOLDER) if os.path.exists(UPLOAD_FOLDER) else []

    return render_template_string(
        BASE_CSS + NAVBAR + UPLOAD_PAGE,
        message=message, msg_type=msg_type, files=files
    )


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


UPLOAD_PAGE = """
<div class="container">
  <h1>Employee Document Upload</h1>
  <div class="card">
    {% if message %}
      <div class="flash {{ 'success' if msg_type == 'success' else '' }}">{{ message }}</div>
    {% endif %}
    <form method="POST" enctype="multipart/form-data">
      <label style="font-size:0.8rem; color:#4b5563;">Select file to upload</label>
      <input type="file" name="file">
      <button type="submit">Upload</button>
    </form>
    {% if files %}
      <h3 style="margin-top:1.5rem; font-size:0.9rem; color:#111827;">Uploaded Files</h3>
      <table>
        <tr><th>Filename</th><th>Action</th></tr>
        {% for f in files %}
        <tr>
          <td>{{ f }}</td>
          <td><a href="/uploads/{{ f }}" class="btn" style="padding:0.3rem 0.8rem; font-size:0.75rem;">View</a></td>
        </tr>
        {% endfor %}
      </table>
    {% endif %}
  </div>
</div>
"""


@app.route("/docs")
def docs():
    if not session.get("user"):
        flash("Please log in first.")
        return redirect(url_for("login"))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM confidential_docs")
    documents = c.fetchall()
    conn.close()

    return render_template_string(BASE_CSS + NAVBAR + DOCS_PAGE, docs=documents)


DOCS_PAGE = """
<div class="container">
  <h1>Confidential Documents</h1>
  <div class="card">
    <p style="font-size:0.8rem; color:#6b7280; margin-bottom:1rem;">
      Logged in as: <strong style="color:#1d4ed8;">{{ session['user'] }}</strong>
      ({{ session.get('role', 'unknown') }})
    </p>
    <table>
      <tr><th>ID</th><th>Title</th><th>Content</th><th>Owner</th></tr>
      {% for doc in docs %}
      <tr>
        <td>{{ doc['id'] }}</td>
        <td>{{ doc['title'] }}</td>
        <td style="color:#92400e;">{{ doc['content'] }}</td>
        <td>{{ doc['owner'] }}</td>
      </tr>
      {% endfor %}
    </table>
  </div>
</div>
"""


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
