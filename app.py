import os
from flask import Flask, render_template, request, redirect, url_for, flash
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from dotenv import load_dotenv

load_dotenv()

# --- Настройки приложения ---
app = Flask(__name__, instance_relative_config=True)
app.secret_key = os.getenv('SECRET_KEY', 'dev_secret')

# --- Пути и база ---
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Flask-Login ---
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# --- Модели ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    type = db.Column(db.String(50))
    photo_path = db.Column(db.String(255))
    status = db.Column(db.String(50), default='pending')

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- Основные страницы ---
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

# --- Аутентификация (вход и регистрация на одной странице) ---
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if current_user.is_authenticated:
        return redirect(url_for('cabinet'))

    if request.method == 'POST':
        action = request.form.get('action')  # "login" или "register"
        email = request.form.get('email')
        password = request.form.get('password')

        if action == 'login':
            user = User.query.filter_by(email=email).first()
            if user and check_password_hash(user.password_hash, password):
                login_user(user)
                return redirect(url_for('cabinet'))
            flash("Неверный email или пароль", "danger")

        elif action == 'register':
            if User.query.filter_by(email=email).first():
                flash("Email уже зарегистрирован", "warning")
            else:
                hashed = generate_password_hash(password)
                new_user = User(email=email, password_hash=hashed)
                db.session.add(new_user)
                db.session.commit()
                flash("Регистрация успешна! Теперь войдите в систему.", "success")

    return render_template('dashboard.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash("Вы вышли из аккаунта", "info")
    return redirect(url_for('index'))

# --- Кабинет ---
@app.route('/cabinet')
@login_required
def cabinet():
    orders = Order.query.filter_by(user_id=current_user.id).all()
    return render_template('cabinet.html', user=current_user, orders=orders)

# --- Загрузка файлов ---
@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    file = request.files.get('file')
    order_type = request.form.get('order_type', 'single')

    if not file:
        flash("Файл не выбран", "warning")
        return redirect(request.url)

    filename = secure_filename(file.filename)
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    new_order = Order(user_id=current_user.id, type=order_type, photo_path=file_path, status='pending')
    db.session.add(new_order)
    db.session.commit()

    flash("Файл успешно загружен!", "success")
    return redirect(url_for('cabinet'))

if __name__ == '__main__':
    app.run(debug=True)
