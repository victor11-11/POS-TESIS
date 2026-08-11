from flask import Flask
from werkzeug.security import generate_password_hash
from models import db, Product, Presentation, User
from routes import bp

app = Flask(__name__)
app.config['SECRET_KEY'] = 'pos-odoo-teg-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pos_tesis.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
app.register_blueprint(bp)

with app.app_context():
    db.create_all()

    if not User.query.first():
        admin_user = User(
            username='admin',
            password=generate_password_hash('admin123'),
            nombre_completo='Administrador',
            cargo='Administrador'
        )
        db.session.add(admin_user)
        db.session.commit()

    if not Product.query.first():
        # Usamos image en lugar de icon
        p1 = Product(name='Paracetamol 500mg', price=5.00, stock=100, category='medicamento', image='default.png')
        db.session.add(p1)
        db.session.commit()
        db.session.add(Presentation(name='Caja x10 Tabletas', product_id=p1.id))
        db.session.add(Presentation(name='Jarabe 100ml', product_id=p1.id))
        db.session.commit()

        p2 = Product(name='Agua Mineral 600ml', price=1.50, stock=50, category='bebida', image='default.png')
        db.session.add(p2)
        db.session.commit()

if __name__ == '__main__':
    app.run(debug=True, port=5000)