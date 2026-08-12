from datetime import datetime
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    nombre_completo = db.Column(db.String(100), nullable=False)
    cargo = db.Column(db.String(50), nullable=False)  # Ej: Cajero, Administrador, Supervisor

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cedula = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    sales = db.relationship('Sale', backref='client', lazy=True)

    @property
    def tipo(self):
        """Determina el tipo de persona según el prefijo de la cédula/RIF.
        Retorna 'J' para persona jurídica (RIF que inicia con 'J'),
        'V' para persona natural (cedula que inicia con 'V'), o 'O' para otro."""
        if not self.cedula:
            return 'O'
        c = self.cedula.strip().upper()
        if len(c) == 0:
            return 'O'
        first = c[0]
        if first == 'J':
            return 'J'
        if first == 'V':
            return 'V'
        return 'O'

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(50), nullable=False, default='medicamento')
    image = db.Column(db.String(200), default='default.png')
    presentations = db.relationship('Presentation', backref='product', lazy=True, cascade='all, delete-orphan')

class Presentation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    total = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=True)