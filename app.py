from flask import Flask, render_template, request, redirect, url_for, session, flash
from passlib.hash import bcrypt
import mysql.connector
import pyshorteners
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key'

url_mapping = {}

# Database Configuration
db_config = {
    'host': 'localhost',
    'user': 'your_username',
    'password': 'your_password',
    'database': 'Database_name'
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

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
        return str(e)
    

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
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
        conn.commit()
        cursor.close()
        conn.close()
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

# Route: Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user and bcrypt.verify(password, user['password']):
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')

# Route: Dashboard (Protected)
@app.route('/dashboard', methods=['GET', 'POST'])
@login_required  # Protect this route with the login_required decorator
def dashboard():
    short_url = ""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        long_url = request.form['long_url']
        short_url = shorten_url(long_url)
        username = session['username']  # Retrieve the username from the session

        # Insert new URL data into the database
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("INSERT INTO data (username, long_url, short_url) VALUES (%s, %s, %s)", 
                       (username, long_url, short_url))
        conn.commit()
        cursor.close()
        conn.close()

    # Retrieve the user's URL data
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    query = "SELECT id, long_url, short_url, created_at FROM data WHERE username = %s"
    cursor.execute(query, (session['username'],))  # Use session['username'] to filter data
    urls = cursor.fetchall()  # Fetch all the results
    cursor.close()
    conn.close()

    return render_template("dashboard.html", urls=urls, username=session['username'], short_url=short_url)



# Route: Logout
@app.route('/logout')
@login_required  # Protect this route with the login_required decorator
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
