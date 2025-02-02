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

#'LostNFound.mysql.pythonanywhere-services.com', database='LostNFound$default', user='LostNFound', password='"*********"'

sql_host = "**.***.(ythonanywhere-services.com"
sql_user = "LostNFound"
sql_password = "*********"
sql_database = "LostNFound$default"

app = Flask(__name__)
app.secret_key = 'your_secret_key'
UPLOAD_FOLDER = '/home/LostNFound/mysite/static/images'  
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg','webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=7)

class User(UserMixin):
    def __init__(self, id):
        self.id = id

def create_connection():
    return mysql.connector.connect(
        host=sql_host,
        database=sql_database,
        user=sql_user,
        password=sql_password
    )

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
        latitude FLOAT,
        longitude FLOAT,
        contact_info VARCHAR(100)
    );""")
    cursor.execute("INSERT IGNORE INTO user (username, password) VALUES ('temp', 'temp');")
    connection.commit()
    cursor.close()
    connection.close()

create_tables()

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

    cursor.execute("SELECT id, name, description, category, status, priority, image_path, location, contact_info, date  FROM items order by date desc")
    items = cursor.fetchall()

    cursor.close()
    connection.close()

    return items
def get_items_from_db_prior():
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
    items_prior = get_items_from_db_prior()
    total_lost = 0
    total_found = 0
    total_items = len(items)
    admin_status = is_admin(current_user.id)

    for i, item in enumerate(items):
        try:
            priority = int(item[5])
        except ValueError:
            priority = 0

        items[i] = list(item) 
        items[i][5] = priority


        if item[4] == 'lost':
            total_lost += 1
        elif item[4] == 'found':
            total_found += 1
    for i, item in enumerate(items_prior):
        try:
            priority = int(item[5])
        except ValueError:
            priority = 0

        items_prior[i] = list(item)  
        items_prior[i][5] = priority


    recent_items = items_prior[:10]

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

    items_list = []  

    for item in items:
        formatted_item = f'item name: *{item[2]}*\n'  
        formatted_item += f'desc: {item[3]}\n'  
        formatted_item += f'status: *{item[5]}*\n'  
        formatted_item += f'location: {item[8]}\n' 
        formatted_item += f'contact: {item[9]}\n' 
        formatted_item += '------'*10 + '\n'  
        items_list.append(formatted_item)

    items_list.append("View all at website: https://lostnfound.pythonanywhere.com/login")

    formatted_data = ''.join(items_list)

    return render_template('view_items.html', items=formatted_data)
@app.route('/modify_item/<int:item_id>', methods=['GET', 'POST'])
def modify_item(item_id):
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        priority = request.form['priority']
        category = request.form['category']
        status = request.form['status']
        location = request.form['location']
        contact_info = request.form['contact_info']
        image_path = request.files.get('image_path') 
        if image_path:
            image_filename = secure_filename(image_path.filename)
            image_path.save(os.path.join('/home/LostNFound/mysite/static/uploads', image_filename))
            image_path = os.path.join('/home/LostNFound/mysite/static/uploads', image_filename)
        else:
            image_path = None 

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
        return redirect(url_for('dashboard'))  

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

    cursor.execute("SELECT image_path FROM items WHERE id = %s", (item_id,))
    item = cursor.fetchone()

    if item:
        image_path = item[0]  
        image_path = "/home/LostNFound/mysite/static"+image_path
        print(f"Full image path: {image_path}")

        cursor.execute("DELETE FROM items WHERE id = %s", (item_id,))
        connection.commit()

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
    user_id = current_user.id
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT * FROM user WHERE id = %s", (user_id,))
    user_data = cursor.fetchone()
    if user_data and user_data['username'] == 'temp':
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
        latitude = request.form.get('latitude')  
        longitude = request.form.get('longitude')  

        file = request.files['image']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            image_folder = '/home/LostNFound/mysite/static/images/'
            if not os.path.exists(image_folder):
                os.makedirs(image_folder)

            image_path = os.path.join(image_folder, filename)

            try:
                img = Image.open(file)

                target_width, target_height = 1280, 720
                original_width, original_height = img.size
                original_ratio = original_width / original_height
                target_ratio = target_width / target_height

                if original_ratio > target_ratio:
                    new_width = target_width
                    new_height = int(target_width / original_ratio)
                else:
                    new_height = target_height
                    new_width = int(target_height * original_ratio)

                img = img.resize((new_width, new_height), Image.LANCZOS)

                from PIL import ImageStat
                avg_color = tuple(int(c) for c in ImageStat.Stat(img).mean[:3])
                final_img = Image.new("RGB", (target_width, target_height), avg_color)
                offset_x = (target_width - new_width) // 2
                offset_y = (target_height - new_height) // 2
                final_img.paste(img, (offset_x, offset_y))

                final_img.save(image_path, format='JPEG', quality=85)

                image_db_path = "/images/" + filename
            except Exception as e:
                print(f"Error processing image: {e}")
                flash("Image upload failed. Please try again.", "danger")
                return redirect(url_for('report'))

            try:
                query = """
                    INSERT INTO items (priority, name, description, category, status, image_path, date, location, contact_info, latitude, longitude, user)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                values = (priority, name, description, category, status, image_db_path, date, location, contact_info, latitude, longitude, user_data['username'].capitalize())
                cursor.execute(query, values)
                connection.commit()

                flash("Report successfully submitted!", "success")
                return redirect(url_for('dashboard'))
            except Exception as e:
                print(f"Error inserting into database: {e}")
                flash("Failed to submit report. Please try again later.", "danger")
                return redirect(url_for('report'))
        else:
            flash("Invalid file format. Please upload a valid image.", "danger")
            return redirect(url_for('report'))

    return render_template('return.html')

@app.route('/show_locations')
@login_required
def show_locations():
    connection = create_connection()
    cursor = connection.cursor()
    cursor.execute("SELECT name, status, latitude, longitude, contact_info,image_path FROM items")
    lost_items = cursor.fetchall()
    cursor.close()

    for i in range(len(lost_items)):
        lost_items[i] = list(lost_items[i])  
        lost_items[i][2] = float(lost_items[i][2]) 
        lost_items[i][3] = float(lost_items[i][3])  
        #image_path = lost_items[i][5]  # e.g., /images/filename
        #lost_items[i][5] = "/home/LostNFound/mysite/static"+image_path


    return render_template('show_locations.html', lost_items=lost_items)

@app.route('/create', methods=['GET', 'POST'])
def create():
    cookie_limit = request.cookies.get('rate_limit')

    if request.method == 'POST':
        if cookie_limit:
            last_request_time = datetime.strptime(cookie_limit, '%Y-%m-%d %H:%M:%S')
            if datetime.now() - last_request_time < timedelta(seconds=60):
                flash('You are being rate-limited. Please wait a minute before trying again.')
                return redirect(url_for('create'))

        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash("Passwords don't match. Please try again.")
            return redirect(url_for('create'))

        connection = create_connection() 
        cursor = connection.cursor()

        cursor.execute("SELECT * FROM user WHERE username = %s", (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            flash("Username or email already exists. Please choose another one.")
            return redirect(url_for('create'))

        cursor.execute("INSERT INTO user (username, password, role) VALUES (%s, %s, %s)",
                       (username, password, 'user'))
        connection.commit()

        cursor.close()
        connection.close()

        flash("Account created successfully! You can now log in.")

        response = make_response(redirect(url_for('login')))
        response.set_cookie('rate_limit', datetime.now().strftime('%Y-%m-%d %H:%M:%S'), max_age=timedelta(minutes=1))
        logging.debug("Setting rate-limit cookie.") 
        return response

    return render_template('create.html')



@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)
    user = current_user.id

    cursor.execute("SELECT * FROM user WHERE id = %s", (user,))
    na = cursor.fetchone()
    user=na['username']
    cursor.execute("SELECT * FROM items WHERE user = %s", (user,))
    posts = cursor.fetchall()
    if not posts:
        posts = [1]
    if request.method == 'POST':
        post_id = request.form.get('post_id')
        if post_id:
            cursor.execute("SELECT * FROM items WHERE id = %s AND user = %s", (post_id, user))
            post_to_delete = cursor.fetchone()

            if post_to_delete:
                cursor.execute("DELETE FROM items WHERE id = %s", (post_id,))
                connection.commit()

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