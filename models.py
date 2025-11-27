from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100))
    phone = db.Column(db.String(30))
    confirmed = db.Column(db.Boolean, default=False)
    confirm_token = db.Column(db.String(255), nullable=True)
    
    is_admin = db.Column(db.Boolean, default=False)
    
    orders = db.relationship('Order', backref='user', lazy=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    photo_filename = db.Column(db.String(200))
    figurine_type = db.Column(db.String(100))
    size = db.Column(db.String(50))
    comments = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(50), default='ожидает оплаты')