from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE, password TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, type TEXT, photo_path TEXT, status TEXT)''')
    conn.commit()
    conn.close()

init_db()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Маршруты для страниц
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/single')
def single():
    return render_template('single.html')

@app.route('/family')
def family():
    return render_template('family.html')

@app.route('/couple')
def couple():
    return render_template('couple.html')

@app.route('/wedding')
def wedding():
    return render_template('wedding.html')

@app.route('/anime')
def anime():
    return render_template('anime.html')

@app.route('/styles')
def styles():
    return render_template('styles.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect('orders.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['user_id'] = user[0]
            return redirect(url_for('dashboard'))
        return render_template('login.html', error="Неверные данные")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = sqlite3.connect('orders.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password))
            conn.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conn.close()
            return render_template('register.html', error="Email уже зарегистрирован")
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE user_id = ?", (session['user_id'],))
    orders = c.fetchall()
    conn.close()
    return render_template('dashboard.html', orders=orders)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if 'file' not in request.files:
        return redirect(request.url)
    file = request.files['file']
    order_type = request.form.get('order_type', 'single')
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        conn = sqlite3.connect('orders.db')
        c = conn.cursor()
        c.execute("INSERT INTO orders (user_id, type, photo_path, status) VALUES (?, ?, ?, ?)",
                  (session['user_id'], order_type, file_path, 'pending'))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    return redirect(request.url)

if __name__ == '__main__':
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True)