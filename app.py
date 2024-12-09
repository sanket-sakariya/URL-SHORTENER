from flask import Flask, render_template, request, redirect, url_for, session, flash
from passlib.hash import bcrypt
import mysql.connector
import pyshorteners
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database Configuration
db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': 'sanket1122005',
    'database': 'URLS'
}

def get_db_connection():
    try:
        return mysql.connector.connect(**db_config)
    except mysql.connector.Error as e:
        flash(f"Database connection error: {e}", 'danger')
        return None

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Function to shorten the URL
def shorten_url(long_url):
    try:
        # Using TinyURL shortener service
        s = pyshorteners.Shortener()
        return s.tinyurl.short(long_url)
    except Exception as e:
        flash(f"Error shortening URL: {e}", 'danger')
        return None

# Route: Redirect root URL to login
@app.route('/')
def index():
    return redirect(url_for('login'))

# Route: Signup
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = bcrypt.hash(password)
        
        conn = get_db_connection()
        if conn is None:
            return redirect(url_for('signup'))
        
        try:
            cursor = conn.cursor(dictionary=True)
            # Check if the username already exists
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            if user:
                flash('Username already exists. Please choose another.', 'warning')
                return redirect(url_for('signup'))
            
            # Insert new user into the database
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (%s, %s)", 
                (username, hashed_password)
            )
            conn.commit()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.Error as e:
            flash(f"Error creating account: {e}", 'danger')
        finally:
            cursor.close()
            conn.close()
    return render_template('signup.html')


# Route: Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        if conn is None:
            return redirect(url_for('login'))
        
        try:
            cursor = conn.cursor(dictionary=True)
            # Check if the username exists
            cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cursor.fetchone()
            if not user:
                flash('Username does not exist. Please sign up.', 'warning')
                return redirect(url_for('signup'))
            
            # Verify password
            if bcrypt.verify(password, user['password']):
                session['user_id'] = user['id']
                session['username'] = user['username']
                flash('Logged in successfully!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Incorrect password. Please try again.', 'danger')
        except mysql.connector.Error as e:
            flash(f"Error during login: {e}", 'danger')
        finally:
            cursor.close()
            conn.close()
    return render_template('login.html')


# Route: Dashboard (Protected)
@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    short_url = ""
    if request.method == 'POST':
        long_url = request.form['long_url']
        username = session['username']
        
        conn = get_db_connection()
        if conn is None:
            return redirect(url_for('dashboard'))
        
        try:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT short_url FROM data WHERE username = %s AND long_url = %s"
            cursor.execute(query, (username, long_url))
            result = cursor.fetchone()
            
            if result:
                short_url = result['short_url']
            else:
                short_url = shorten_url(long_url)
                if short_url:
                    cursor.execute(
                        "INSERT INTO data (username, long_url, short_url) VALUES (%s, %s, %s)", 
                        (username, long_url, short_url)
                    )
                    conn.commit()
        except mysql.connector.Error as e:
            flash(f"Error processing URL: {e}", 'danger')
        finally:
            cursor.close()
            conn.close()

    conn = get_db_connection()
    if conn is None:
        return redirect(url_for('dashboard'))
    
    try:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT id, long_url, short_url, created_at FROM data WHERE username = %s"
        cursor.execute(query, (session['username'],))
        urls = cursor.fetchall()
    except mysql.connector.Error as e:
        flash(f"Error fetching URLs: {e}", 'danger')
        urls = []
    finally:
        cursor.close()
        conn.close()

    return render_template("dashboard.html", urls=urls, username=session['username'], short_url=short_url)

# Route: Logout
@app.route('/logout')
@login_required
def logout():
    session.clear()
    return redirect(url_for('login'))

# Error Handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True)
