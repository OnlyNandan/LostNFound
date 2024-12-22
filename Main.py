from flask import Flask, render_template, redirect, url_for, request, flash, session, jsonify, current_app, make_response
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import timedelta
import mysql.connector
import os
from werkzeug.utils import secure_filename
from PIL import Image, ImageOps
import os
from werkzeug.utils import secure_filename
from io import BytesIO
from datetime import datetime, timedelta
import logging
logging.basicConfig(level=logging.DEBUG)

# Set a maximum image size and quality level for compression
MAX_IMAGE_SIZE = (800, 600)  # Max dimensions (width, height)
QUALITY = 85  # Image quality (0-100)

#'LostNFound.mysql.pythonanywhere-services.com', database='LostNFound$default', user='LostNFound', password='secretpassword'

# Database credentials
sql_host = "LostNFound.mysql.pythonanywhere-services.com"
sql_user = "LostNFound"
sql_password = "secretpassword"
sql_database = "LostNFound$default"

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your_secret_key'
UPLOAD_FOLDER = '/home/LostNFound/mysite/static/images'  # Folder to store uploaded images
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg','webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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

def get_items_from_db():
    connection = create_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT id, name, description, category, status, priority, image_path, location, contact_info, date  FROM items order by priority desc")
    items = cursor.fetchall()

    cursor.close()
    connection.close()

    return items

def is_admin(user_id):
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)

    query = "SELECT role FROM user WHERE id = %s "
    cursor.execute(query, (user_id,))
    result = cursor.fetchone()

    cursor.close()
    connection.close()

    if result and result['role'] == 'admin':
        return True
    return False

@app.route('/dashboard')
@login_required
def dashboard():
    items = get_items_from_db()
    total_lost = 0
    total_found = 0
    total_items = len(items)
    admin_status = is_admin(current_user.id)

    for i, item in enumerate(items):
        try:
            priority = int(item[5])
        except ValueError:
            priority = 0

        items[i] = list(item)  # Convert tuple to list
        items[i][5] = priority


        if item[4] == 'lost':
            total_lost += 1
        elif item[4] == 'found':
            total_found += 1
    recent_items = items[:10]

    return render_template('dashboard.html',
                           user=get_user_info(),
                           items=items,
                           total_items=total_items,
                           total_lost=total_lost,
                           total_found=total_found,
                           recent_items=recent_items,
                           admin_status=admin_status)

@app.route('/admin_dashboard')
def admin_dashboard():
    connection = create_connection()
    cursor = connection.cursor()

    # Get all items from the database
    cursor.execute("SELECT * FROM items order by date desc")
    items = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('admin_dashboard.html', items=items)

@app.route('/view_items')
def view_items():
    connection = create_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT * FROM items ORDER BY date DESC")
    items = cursor.fetchall()

    cursor.close()
    connection.close()

    items_list = []  # Create a new list to store formatted items

    for item in items:
        formatted_item = f'item name: *{item[2]}*\n'  # Name
        formatted_item += f'desc: {item[3]}\n'  # Description
        formatted_item += f'status: *{item[5]}*\n'  # Status (lost/found)
        formatted_item += f'location: {item[8]}\n'  # Location
        formatted_item += f'contact: {item[9]}\n'  # Contact
        formatted_item += '------'*10 + '\n'  # Separator
        items_list.append(formatted_item)

    items_list.append("View all at website: https://lostnfound.pythonanywhere.com/login")

    formatted_data = ''.join(items_list)

    return render_template('view_items.html', items=formatted_data)
@app.route('/modify_item/<int:item_id>', methods=['GET', 'POST'])
def modify_item(item_id):
    if request.method == 'POST':
        # Get the data from the form
        name = request.form['name']
        description = request.form['description']
        priority = request.form['priority']
        category = request.form['category']
        status = request.form['status']
        location = request.form['location']
        contact_info = request.form['contact_info']
        image_path = request.files.get('image_path')  # Image upload (optional)

        # Handling image upload (if provided)
        if image_path:
            image_filename = secure_filename(image_path.filename)
            image_path.save(os.path.join('/home/LostNFound/mysite/static/uploads', image_filename))
            image_path = os.path.join('/home/LostNFound/mysite/static/uploads', image_filename)
        else:
            image_path = None  # Keep previous image path if no new image is uploaded

        # Update the database
        connection = create_connection()
        cur = connection.cursor()
        cur.execute("""
            UPDATE items
            SET name = %s, description = %s, priority = %s, category = %s,
                status = %s, location = %s, contact_info = %s, image_path = %s
            WHERE id = %s
        """, (name, description, priority, category, status, location, contact_info, image_path, item_id))
        mysql.connection.commit()
        cur.close()

        flash("Item updated successfully!", "success")
        return redirect(url_for('dashboard'))  # Redirect to the dashboard

    # Retrieve the current item details
    connection = create_connection()
    cur = connection.cursor()
    cur.execute("SELECT * FROM items WHERE id = %s", [item_id])
    item = cur.fetchone()
    cur.close()

    if item:
        return render_template('modify_item.html', item=item)
    else:
        flash("Item not found", "danger")
        return redirect(url_for('dashboard'))



@app.route('/delete_item/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    connection = create_connection()
    cursor = connection.cursor()

    # Get the image path of the item before deleting it
    cursor.execute("SELECT image_path FROM items WHERE id = %s", (item_id,))
    item = cursor.fetchone()

    if item:
        image_path = item[0]  # e.g., /images/filename
        image_path = "/home/LostNFound/mysite/static"+image_path
        print(f"Full image path: {image_path}")

        # Delete the item from the database
        cursor.execute("DELETE FROM items WHERE id = %s", (item_id,))
        connection.commit()

        # If the image exists, delete it
        if os.path.exists(image_path):
            os.remove(image_path)
            print("Image deleted successfully!")
        else:
            print(f"Image file not found: {image_path}")

    cursor.close()
    connection.close()

    return redirect(url_for('admin_dashboard'))



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

@app.route('/report', methods=['GET', 'POST'])
@login_required
def report():
    user = current_user.id  # Get the current user's ID
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM user WHERE id = %s", (user,))
    user_data = cursor.fetchone()
    if user_data and user_data['username'] == 'temp':
        # User is 'temp', return a custom message
        return render_template('create.html', temp_user=True)

    if request.method == 'POST':
        priority = request.form['priority']
        name = request.form['name']
        description = request.form['description']
        category = request.form['category']
        status = request.form['status']
        date = request.form['date']
        location = request.form['location']
        contact_info = request.form['contact_info']

        # Handle file upload
        file = request.files['image']
        image_path = None
        image_folder = '/home/LostNFound/mysite/static/images/'
        if not os.path.exists(image_folder):
            os.makedirs(image_folder)
        if file and allowed_file(file.filename):
            # Compress the image
            filename = secure_filename(file.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        # Open and compress the image using Pillow
        img = Image.open(file)

        # Target dimensions for 16:9 aspect ratio
        target_width = 1280
        target_height = 720
        target_size = (target_width, target_height)

        # Resize the image to fit within the target size while maintaining the aspect ratio
        img.thumbnail(target_size, Image.LANCZOS)

        # Create a new image with a black background (16:9 aspect ratio)
        new_img = Image.new("RGB", target_size, color=(200, 200, 200))

        # Center the resized image on the 16:9 canvas
        offset_x = (target_width - img.width) // 2
        offset_y = (target_height - img.height) // 2
        new_img.paste(img, (offset_x, offset_y))

        # Save the resized image with reduced quality
        with BytesIO() as img_io:
            # Save the resized image to a BytesIO object
            new_img.save(img_io, format='JPEG', quality=QUALITY)  # QUALITY is your compression level
            img_io.seek(0)

            # Write the BytesIO content to the final file
            with open(image_path, 'wb') as f:
                f.write(img_io.read())

        # Return the image path for further use
        ip = "/images/" + filename

        # Insert data into the database
        user = current_user.id
        connection = create_connection()

        # Ensure to use DictCursor to get results as dictionaries
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM user WHERE id = %s", (user,))
        na = cursor.fetchone()

        if na:
            # Ensure na['username'] is a valid field before trying to capitalize
            na['username'] = na['username'].capitalize()

            query = """
                INSERT INTO items (priority, name, description, category, status, image_path, date, location, contact_info, user)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (priority, name, description, category, status, ip, date, location, contact_info, na['username'])

            cursor.execute(query, values)
            connection.commit()

        return redirect(url_for('dashboard'))  # Redirect to dashboard after submission

    return render_template('return.html')  # Render the HTML form

@app.route('/create', methods=['GET', 'POST'])
def create():
    # Check the rate-limit cookie on GET request for the create page
    cookie_limit = request.cookies.get('rate_limit')

    if request.method == 'POST':
        # On POST, check for the rate-limit cookie to apply the rate limit
        if cookie_limit:
            last_request_time = datetime.strptime(cookie_limit, '%Y-%m-%d %H:%M:%S')
            if datetime.now() - last_request_time < timedelta(seconds=60):
                # If rate-limited, redirect to login
                flash('You are being rate-limited. Please wait a minute before trying again.')
                return redirect(url_for('create'))

        # Extract the form data
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Check if passwords match
        if password != confirm_password:
            flash("Passwords don't match. Please try again.")
            return redirect(url_for('create'))

        # Check if the username or email already exists in the database
        connection = create_connection()  # Assuming you have a create_connection function defined
        cursor = connection.cursor()

        cursor.execute("SELECT * FROM user WHERE username = %s", (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            flash("Username or email already exists. Please choose another one.")
            return redirect(url_for('create'))

        # Insert the new user into the database with a default 'user' role
        cursor.execute("INSERT INTO user (username, password, role) VALUES (%s, %s, %s)",
                       (username, password, 'user'))
        connection.commit()

        cursor.close()
        connection.close()

        flash("Account created successfully! You can now log in.")

        # Set the rate-limit cookie after form submission (POST request)
        response = make_response(redirect(url_for('login')))
        response.set_cookie('rate_limit', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), max_age=timedelta(minutes=1))
        logging.debug("Setting rate-limit cookie.")  # Log that the cookie is being set
        return response

    # For GET request, allow access to the create form
    return render_template('create.html')



@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)
    user = current_user.id

    # Fetch user data
    cursor.execute("SELECT * FROM user WHERE id = %s", (user,))
    na = cursor.fetchone()
    user=na['username']
    # Fetch posts created by the user
    cursor.execute("SELECT * FROM items WHERE user = %s", (user,))
    posts = cursor.fetchall()
    if not posts:
        posts = [1]
    # Handle post deletion
    if request.method == 'POST':
        post_id = request.form.get('post_id')
        if post_id:
            # Delete post if it belongs to the current user
            cursor.execute("SELECT * FROM items WHERE id = %s AND user = %s", (post_id, user))
            post_to_delete = cursor.fetchone()

            if post_to_delete:
                # Delete the post from the database
                cursor.execute("DELETE FROM items WHERE id = %s", (post_id,))
                connection.commit()

                # Optionally, handle image deletion from the file system
                if post_to_delete['image_path']:
                    image_path = os.path.join(app.config['UPLOAD_FOLDER'], post_to_delete['image_path'])
                    if os.path.exists(image_path):
                        os.remove(image_path)

                flash('Post deleted successfully', 'success')
                return redirect(url_for('profile'))

    cursor.close()
    connection.close()

    return render_template('profile.html', user=na, posts=posts)
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