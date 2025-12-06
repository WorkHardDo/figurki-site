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

from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer

# email config
app.config['MAIL_SERVER'] = os.getenv("MAIL_SERVER")
app.config['MAIL_PORT'] = int(os.getenv("MAIL_PORT", 465))
app.config['MAIL_USE_SSL'] = os.getenv("MAIL_USE_SSL", "True") == "True"
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config['MAIL_DEFAULT_SENDER'] = os.getenv("MAIL_DEFAULT_SENDER")

mail = Mail(app)
serializer = URLSafeTimedSerializer(app.secret_key)

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

    name = db.Column(db.String(100))
    phone = db.Column(db.String(30))
    address = db.Column(db.String(255))
    confirmed = db.Column(db.Boolean, default=False)
    confirm_token = db.Column(db.String(255), nullable=True)

    is_admin = db.Column(db.Boolean, default=False)

    orders = db.relationship('Order', backref='user', lazy=True)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    photo_filename = db.Column(db.String(255), nullable=False)
    figurine_type = db.Column(db.String(50), nullable=False)
    size = db.Column(db.String(50), nullable=False)
    comments = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='ожидает оплаты')


def send_confirmation_email(user):
    token = serializer.dumps(user.email, salt="email-confirm")

    confirm_url = url_for('confirm_email', token=token, _external=True)

    msg = Message(
        subject="Активация аккаунта на сайте",
        recipients=[user.email],
        body=f"Здравствуйте!\n\nДля активации аккаунта перейдите по ссылке:\n{confirm_url}\n\nЕсли это были не вы — проигнорируйте письмо."
    )

    mail.send(msg)


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

from functools import wraps

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Доступ запрещён", "danger")
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return wrapper

@app.route('/admin/orders')
@admin_required
def admin_orders():
    sort = request.args.get("sort", "desc")
    hide_done = request.args.get("hide_done") == "1"
    paid_only = request.args.get("paid_only") == "1"

    # БАЗОВЫЙ запрос
    query = Order.query

    # Скрыть готовые
    if hide_done:
        query = query.filter(Order.status != "готово")

    # Показать только оплаченные (т.е. "в процессе")
    if paid_only:
        query = query.filter(Order.status == "в процессе")

    # Сортировка
    if sort == "asc":
        orders = query.order_by(Order.created_at.asc()).all()
    else:
        orders = query.order_by(Order.created_at.desc()).all()

    # Цена
    def get_price(size):
        if size == "small": return 3990
        if size == "medium": return 5990
        if size == "large": return 7990
        return 0

    for o in orders:
        o.price = get_price(o.size)

    return render_template(
        "admin.html",
        orders=orders,
        sort=sort,
        hide_done=hide_done,
        paid_only=paid_only
    )


@app.route("/admin/order_done/<int:order_id>", methods=["POST"])
@admin_required
def admin_order_done(order_id):
    order = Order.query.get(order_id)

    if not order:
        return jsonify({"status": "error", "message": "Заказ не найден"}), 404

    order.status = "готово"
    db.session.commit()

    return jsonify({"status": "success", "message": "Заказ отмечен как готовый"})

@app.route("/admin")
@login_required
def admin_panel():
    if not current_user.is_admin:
        return redirect(url_for("index"))

    orders = Order.query.order_by(Order.created_at.desc()).all()
    users = User.query.all()

    return render_template("admin.html", orders=orders, users=users)


# --- Аутентификация ---
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    # Если пользователь уже вошёл — ведём в кабинет
    if current_user.is_authenticated:
        return redirect(url_for('cabinet'))

    if request.method == 'POST':
        action = request.form.get('action')  # login / register

        # ---------------------- ЛОГИН ----------------------
        if action == 'login':
            email = request.form.get('email')
            password = request.form.get('password')

            user = User.query.filter_by(email=email).first()

            if not user:
                flash("Неверный email или пароль", "danger")
                return redirect(url_for('dashboard'))

            if not check_password_hash(user.password_hash, password):
                flash("Неверный email или пароль", "danger")
                return redirect(url_for('dashboard'))

            if not user.confirmed:
                flash("Подтвердите email, прежде чем войти.", "warning")
                return redirect(url_for('dashboard'))

            login_user(user)
            return redirect(url_for('cabinet'))
        # ------------------- РЕГИСТРАЦИЯ -------------------
        elif action == 'register':
            name = request.form.get("username")
            email = request.form.get("email")
            phone = request.form.get("phone")
            address = request.form.get("address")
            password = request.form.get("password")
            confirm = request.form.get("confirm_password")

            # Проверки
            if User.query.filter_by(email=email).first():
                flash("Этот email уже зарегистрирован", "warning")
                return redirect(url_for('dashboard'))

            if password != confirm:
                flash("Пароли не совпадают", "danger")
                return redirect(url_for('dashboard'))

            # Создание пользователя
            hashed = generate_password_hash(password)
            new_user = User(
                email=email,
                password_hash=hashed,
                name=name,
                phone=phone,
                address=address,
                confirmed=False
            )

        db.session.add(new_user)
        db.session.commit()

        send_confirmation_email(new_user)

        flash("Регистрация успешна! Подтвердите email, чтобы войти.", "success")
        return redirect(url_for('dashboard'))


        flash("Регистрация успешна! Теперь войдите в систему.", "success")
        return redirect(url_for('dashboard'))

    return render_template('dashboard.html')


@app.route('/confirm/<token>')
def confirm_email(token):
    try:
        email = serializer.loads(token, salt="email-confirm", max_age=3600)
    except Exception:
        flash("Ссылка подтверждения недействительна или устарела.", "danger")
        return redirect(url_for('dashboard'))

    user = User.query.filter_by(email=email).first()

    if not user:
        flash("Пользователь не найден", "danger")
        return redirect(url_for('dashboard'))

    if user.confirmed:
        flash("Аккаунт уже подтверждён.", "info")
        return redirect(url_for('dashboard'))

    user.confirmed = True
    user.confirm_token = None
    db.session.commit()

    flash("Ваш email успешно подтверждён! Теперь вы можете войти.", "success")
    return redirect(url_for('dashboard'))



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
    # Получаем все заказы пользователя
    orders = Order.query.filter_by(user_id=current_user.id).all()

    # Функция вычисления цены
    def get_price(size):
        if size == "small":
            return 3990
        elif size == "medium":
            return 5990
        elif size == "large":
            return 7990
        return 0

    # Добавляем динамическое поле price + нормализуем статус
    for o in orders:
        o.price = get_price(o.size)
        if not getattr(o, "status", None):
            o.status = "ожидает оплаты"

    # Реальная статистика
    in_progress = Order.query.filter_by(user_id=current_user.id, status="в процессе").count()
    completed = Order.query.filter_by(user_id=current_user.id, status="готово").count()
    total = Order.query.filter_by(user_id=current_user.id).count()

    return render_template(
        'cabinet.html',
        user=current_user,
        orders=orders,
        in_progress=in_progress,
        completed=completed,
        total=total
    )


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

@app.route('/update_status/<int:order_id>', methods=['POST'])
@login_required
def update_status(order_id):
    order = Order.query.filter_by(id=order_id, user_id=current_user.id).first()
    if not order:
        return jsonify({'status': 'error', 'message': 'Заказ не найден'}), 404

    if order.status == 'ожидает оплаты':
        order.status = 'в процессе'
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Статус обновлён: в процессе'})
    else:
        return jsonify({'status': 'error', 'message': 'Нельзя изменить этот заказ'}), 400

@app.route("/update_profile", methods=["POST"])
@login_required
def update_profile():
    data = request.get_json()

    if not data:
        return jsonify({"status": "error", "message": "Нет данных"}), 400

    name = data.get("name")
    phone = data.get("phone")
    address = data.get("address")

    # Проверки
    if not name:
        return jsonify({"status": "error", "message": "Имя не может быть пустым"}), 400

    # Обновляем пользователя
    current_user.name = name
    current_user.phone = phone
    current_user.address = address

    db.session.commit()

    return jsonify({"status": "success", "message": "Профиль обновлён"})
    
@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
