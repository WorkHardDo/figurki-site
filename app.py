import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# --- Настройки приложения ---
app = Flask(__name__, instance_relative_config=True)
app.secret_key = os.getenv('SECRET_KEY', 'dev_secret')

# --- Пути и база ---
app.config['UPLOAD_FOLDER'] = 'static/uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Единая база для пользователей и заказов
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Flask-Login ---
login_manager = LoginManager(app)
login_manager.login_view = 'dashboard'

# --- Модели ---
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    photo_filename = db.Column(db.String(255), nullable=False)
    figurine_type = db.Column(db.String(50), nullable=False)
    size = db.Column(db.String(50), nullable=False)
    comments = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('orders', lazy=True))

# Создание всех таблиц при старте приложения
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

# --- Аутентификация ---
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

# --- Кабинет пользователя ---
@app.route('/cabinet')
@login_required
def cabinet():
    orders = Order.query.filter_by(user_id=current_user.id).all()
    return render_template('cabinet.html', user=current_user, orders=orders)

# --- Создание заказа ---
@app.route('/create_order', methods=['POST'])
def create_order():
    if not current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    file = request.files.get('photo')
    figurine_type = request.form.get('figurine_type')
    size = request.form.get('size')
    comments = request.form.get('comments')

    if not file or not figurine_type or not size:
        return jsonify({'status': 'error', 'message': 'Заполните все поля и прикрепите фото'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    new_order = Order(
        user_id=current_user.id,
        photo_filename=filename,
        figurine_type=figurine_type,
        size=size,
        comments=comments
    )
    db.session.add(new_order)
    db.session.commit()

    return jsonify({'status': 'success', 'message': 'Заказ успешно создан!'})

if __name__ == '__main__':
    app.run(debug=True)
