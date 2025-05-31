from flask import Flask, render_template, request, redirect, url_for, session, flash
from passlib.hash import bcrypt
import sqlite3
import pyshorteners
from functools import wraps
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'
DATABASE = 'url_shortener.db'

# Ensure DB file and tables exist
def init_db():
    if not os.path.exists(DATABASE):
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT UNIQUE NOT NULL,
                            password TEXT NOT NULL)''')
        cursor.execute('''CREATE TABLE data (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT NOT NULL,
                            long_url TEXT NOT NULL,
                            short_url TEXT NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        conn.commit()
        conn.close()

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def shorten_url(long_url):
    try:
        s = pyshorteners.Shortener()
        return s.tinyurl.short(long_url)
    except Exception as e:
        return str(e)

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = bcrypt.hash(password)

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed_password))
            conn.commit()
            flash('Account created successfully! Please log in.', 'success')
        except sqlite3.IntegrityError:
            flash('Username already exists.', 'danger')
        finally:
            conn.close()
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and bcrypt.verify(password, user['password']):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    short_url = ""
    if request.method == 'POST':
        long_url = request.form['long_url']
        short_url = shorten_url(long_url)
        username = session['username']

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO data (username, long_url, short_url) VALUES (?, ?, ?)", 
                       (username, long_url, short_url))
        conn.commit()
        conn.close()

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, long_url, short_url, created_at FROM data WHERE username = ?", (session['username'],))
    urls = cursor.fetchall()
    conn.close()

    return render_template("dashboard.html", urls=urls, username=session['username'], short_url=short_url)


@app.route('/delete/<int:url_id>')
@login_required
def delete_url(url_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM data WHERE id = ? AND username = ?", (url_id, session['username']))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))



@app.route('/logout')
@login_required
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
