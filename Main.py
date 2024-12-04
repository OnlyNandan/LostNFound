from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import timedelta
import mysql.connector
import os
from werkzeug.utils import secure_filename

# Database credentials
sql_host = "localhost"
sql_user = "root"
sql_password = "secretpassword"
sql_database = "lost_and_found"

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'
UPLOAD_FOLDER = 'static/uploads'  # Folder to store uploaded images
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=7)

# User class
class User(UserMixin):
    def __init__(self, id):
        self.id = id

# Database connection function
def create_connection():
    return mysql.connector.connect(
        host=sql_host,
        database=sql_database,
        user=sql_user,
        password=sql_password
    )

# Create tables
def create_tables():
    connection = create_connection()
    cursor = connection.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        role ENUM('user', 'admin') DEFAULT 'user'
    );""")
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INT AUTO_INCREMENT PRIMARY KEY,
        priority INT DEFAULT 0,
        name VARCHAR(100) NOT NULL,
        description TEXT NOT NULL,
        category VARCHAR(50),
        status ENUM('lost', 'found', 'returned') DEFAULT 'lost',
        image_path VARCHAR(255),
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        location VARCHAR(100),
        contact_info VARCHAR(100)
    );""")
    cursor.execute("INSERT IGNORE INTO user (username, password) VALUES ('temp', 'temp');")
    connection.commit()
    cursor.close()
    connection.close()

create_tables()

# Helper functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@login_manager.user_loader
def load_user(user_id):
    connection = create_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM user WHERE id = %s", (user_id,))
    user_data = cursor.fetchone()
    cursor.close()
    connection.close()
    if user_data:
        return User(user_id)
    return None

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        connection = create_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM user WHERE username = %s AND password = %s", (username, password))
        user_data = cursor.fetchone()
        cursor.close()
        connection.close()
        if user_data:
            user = User(user_data[0])
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid credentials!')
    return render_template('login.html')

@app.route('/continue_without_login', methods=['GET'])
def continue_without_login():
    connection = create_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM user WHERE username = %s AND password = %s", ('temp', 'temp'))
    user_data = cursor.fetchone()
    cursor.close()
    connection.close()
    if user_data:
        user = User(user_data[0])
        login_user(user)
        return redirect(url_for('dashboard'))
    else:
        flash('Temporary user does not exist!')
        return redirect(url_for('login'))
    
# Fetch items from the database
def get_items_from_db():
    connection = create_connection()
    cursor = connection.cursor()

    # SQL query to get items from the database
    cursor.execute("SELECT id, name, description, category, status, priority, image_path, location, contact_info, date  FROM items order by priority desc")
    items = cursor.fetchall()

    # Close the connection
    cursor.close()
    connection.close()

    # Return the list of items
    return items

@app.route('/dashboard')
@login_required
def dashboard():
    items = get_items_from_db()
    
    for i, item in enumerate(items):
        # Check if the priority can be converted to an integer
        try:
            priority = int(item[5])  # Convert priority (index 5) to integer
        except ValueError:
            priority = 0  # Set a default value or handle the case as needed
        
        items[i] = list(item)  # Convert tuple to list
        items[i][5] = priority  # Update the priority field with the correct value
    print(items[4][3])
        
    return render_template('dashboard.html', user=get_user_info(), items=items)

@app.route('/report_lost')
@login_required
def report_lost():
    return render_template('report_lost.html')

@app.route('/report_found')
@login_required
def report_found():
    return render_template('report_found.html')

@app.route('/fetch_items', methods=['GET'])
@login_required
def fetch_items():
    search = request.args.get('search', '').lower()
    category = request.args.get('category', 'all')
    status = request.args.get('status', 'all')
    sort_by = request.args.get('sort', 'priority')

    connection = create_connection()
    cursor = connection.cursor()

    query = "SELECT * FROM items WHERE 1=1"
    params = []

    if category != 'all':
        query += " AND category = %s"
        params.append(category)
    if status != 'all':
        query += " AND status = %s"
        params.append(status)
    if search:
        query += " AND (LOWER(name) LIKE %s OR LOWER(description) LIKE %s)"
        params.append(f"%{search}%")
        params.append(f"%{search}%")

    query += f" ORDER BY {sort_by} DESC"
    cursor.execute(query, params)
    items = cursor.fetchall()
    cursor.close()
    connection.close()

    return jsonify(items)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_item():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        category = request.form['category']
        location = request.form['location']
        contact_info = request.form['contact_info']
        status = request.form['status']
        priority = request.form['priority']
        file = request.files['image']
        image_path = None
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(image_path)
        connection = create_connection()
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO items (name, description, category, status, priority, image_path, location, contact_info)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (name, description, category, status, priority, image_path, location, contact_info))
        connection.commit()
        cursor.close()
        connection.close()
        flash('Item added successfully!')
        return redirect(url_for('dashboard'))
    return render_template('add_item.html')

@app.route('/profile')
@login_required
def profile():
    user_info = get_current_user_info()
    if user_info:
        return f"Logged in as: {user_info['username']} (Role: {user_info['role']})"
    return "User information not available."

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Utility functions
def get_user_info():
    if current_user.is_authenticated:
        connection = create_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM user WHERE id = %s", (current_user.id,))
        user = cursor.fetchone()
        cursor.close()
        connection.close()
        if user:
            return {"id": user[0], "username": user[1], "role": user[3]}
    return None

if __name__ == '__main__':
    app.run(debug=True)