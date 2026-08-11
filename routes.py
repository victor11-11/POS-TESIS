import os
from flask import Blueprint, render_template, redirect, url_for, request, jsonify, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from models import db, Product, Presentation, Sale, Client, User

bp = Blueprint('main', __name__)
cart = []
current_client_id = None
TASA_BCV = 36.50  # Modifica esta tasa cuando lo necesites
CLAVE_MAESTRA_ADMIN = 'admin1234'

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        selected_profile = request.form.get('profile')

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            if selected_profile and user.cargo != selected_profile:
                flash('El perfil seleccionado no coincide con el usuario.', 'danger')
                return redirect(url_for('main.login'))

            session['user_id'] = user.id
            session['user_name'] = user.nombre_completo
            session['user_role'] = user.cargo
            flash('¡Bienvenido al sistema!', 'success')
            return redirect(url_for('main.index'))

        flash('Usuario o contraseña incorrectos', 'danger')

    users = User.query.order_by(User.nombre_completo).all()
    return render_template('login.html', users=users)


@bp.route('/recover', methods=['POST'])
def recover_password():
    username = request.form.get('recover_username', '').strip()
    profile = request.form.get('recover_profile')
    new_password = request.form.get('new_password', '')
    admin_key = request.form.get('admin_key', '')

    if not username or not new_password or not profile:
        flash('Complete todos los campos para la recuperación.', 'warning')
        return redirect(url_for('main.login'))

    user = User.query.filter_by(username=username).first()
    if not user:
        flash('Usuario no encontrado.', 'danger')
        return redirect(url_for('main.login'))

    if user.cargo != profile:
        flash('El perfil seleccionado no coincide con el usuario.', 'danger')
        return redirect(url_for('main.login'))

    if profile == 'Administrador':
        if admin_key != CLAVE_MAESTRA_ADMIN:
            flash('Clave de administrador incorrecta. Recuperación denegada.', 'danger')
            return redirect(url_for('main.login'))

    # Restablecer contraseña
    user.password = generate_password_hash(new_password)
    db.session.commit()
    flash('Contraseña restablecida correctamente. Puede iniciar sesión con la nueva contraseña.', 'success')
    return redirect(url_for('main.login'))

@bp.route('/logout')
def logout():
    session.clear()
    flash('Sesión cerrada', 'info')
    return redirect(url_for('main.login'))

@bp.route('/registrar-usuario', methods=['POST'])
def registrar_usuario():
    admin_secret = request.form.get('admin_secret')
    username = request.form.get('username')
    password = request.form.get('password')
    nombre_completo = request.form.get('nombre_completo')
    cargo = request.form.get('cargo')

    if admin_secret != CLAVE_MAESTRA_ADMIN:
        flash('Clave de administrador incorrecta. No se pudo registrar el usuario.', 'danger')
        return redirect(url_for('main.login'))

    if not username or not password or not nombre_completo or not cargo:
        flash('Todos los campos son obligatorios.', 'warning')
        return redirect(url_for('main.login'))

    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        flash('El nombre de usuario ya está en uso.', 'warning')
        return redirect(url_for('main.login'))

    hashed_password = generate_password_hash(password)
    nuevo_usuario = User(
        username=username,
        password=hashed_password,
        nombre_completo=nombre_completo,
        cargo=cargo,
    )

    db.session.add(nuevo_usuario)
    db.session.commit()

    flash('¡Personal registrado exitosamente! Ya puede iniciar sesión.', 'success')
    return redirect(url_for('main.login'))

@bp.route('/pos')
def pos_view():
    return _render_pos_page()


def _render_pos_page(search_query='', active_cat='all', edit_product=None):
    filtered_products = Product.query
    if active_cat != 'all':
        filtered_products = filtered_products.filter_by(category=active_cat)
    if search_query:
        filtered_products = filtered_products.filter(Product.name.ilike(f'%{search_query}%'))

    products = filtered_products.all()
    total = sum(item['price'] * item['qty'] for item in cart)
    client_obj = Client.query.get(current_client_id) if current_client_id else None

    payments_applied = session.get('payments_applied', [])
    total_paid_bs = sum(p.get('amount', 0) for p in payments_applied)
    total_cart_bs = total * TASA_BCV
    remaining_payment_bs = max(total_cart_bs - total_paid_bs, 0.0)

    return render_template(
        'pos.html',
        products=products,
        cart=cart,
        total=total,
        client=client_obj,
        show_modal=modal_state,
        edit_product=edit_product,
        show_client_modal=show_client_modal,
        show_register_modal=show_register_modal,
        show_form_register=show_form_register,
        temp_cedula=temp_cedula,
        show_invoice=show_invoice,
        show_client_actions_modal=show_client_actions_modal,
        last_sale=Sale.query.get(last_sale_id) if last_sale_id else None,
        last_sale_items=last_sale_items_cache,
        search_query=search_query,
        active_cat=active_cat,
        tasa_bcv=TASA_BCV,
        payments_applied=payments_applied,
        total_paid_bs=total_paid_bs,
        remaining_payment_bs=remaining_payment_bs,
    )

# Variables de control de estado globales
modal_state = False
show_client_modal = False
show_register_modal = False
show_form_register = False
show_client_actions_modal = False
temp_cedula = ""
show_invoice = False
last_sale_id = None
last_sale_items_cache = []

@bp.route('/')
def index():
    global current_client_id, modal_state, show_client_modal, show_register_modal, show_form_register, show_invoice
    search_query = request.args.get('q', '').strip()
    active_cat = request.args.get('cat', 'all')
    return _render_pos_page(search_query=search_query, active_cat=active_cat)

@bp.route('/set-rate', methods=['POST'])
def set_rate():
    global TASA_BCV
    raw_rate = request.form.get('rate', '')
    try:
        TASA_BCV = float(raw_rate)
    except (TypeError, ValueError):
        pass
    return jsonify({'ok': True, 'rate': TASA_BCV})

@bp.route('/client-actions')
def client_actions():
    global show_client_actions_modal, show_client_modal, show_register_modal, show_form_register, show_invoice
    if current_client_id:
        show_client_actions_modal = True
        show_client_modal = False
        show_register_modal = False
        show_form_register = False
        show_invoice = False
        return redirect(url_for('main.index'))
    return redirect(url_for('main.ask_client'))

@bp.route('/change-client')
def change_client():
    global current_client_id, show_client_actions_modal, show_client_modal, show_register_modal, show_form_register, show_invoice
    current_client_id = None
    show_client_actions_modal = False
    show_client_modal = True
    show_register_modal = False
    show_form_register = False
    show_invoice = False
    return redirect(url_for('main.index'))

@bp.route('/cancel-order')
def cancel_order():
    global cart, current_client_id, show_client_actions_modal, show_client_modal, show_register_modal, show_form_register, show_invoice
    cart.clear()
    current_client_id = None
    show_client_actions_modal = False
    show_client_modal = False
    show_register_modal = False
    show_form_register = False
    show_invoice = False
    session.pop('show_payment_screen', None)
    session.pop('payments_applied', None)
    session.pop('payment_simulated', None)
    return redirect(url_for('main.index'))

@bp.route('/close-client-actions')
def close_client_actions():
    global show_client_actions_modal
    show_client_actions_modal = False
    return redirect(url_for('main.index'))

@bp.route('/ask-client')
def ask_client():
    global show_client_modal, show_register_modal, show_form_register, show_invoice, show_client_actions_modal
    show_client_actions_modal = False
    show_client_modal = True
    show_register_modal = False
    show_form_register = False
    show_invoice = False
    return redirect(url_for('main.index'))

@bp.route('/check-client', methods=['POST'])
def check_client():
    global current_client_id, show_client_modal, show_register_modal, temp_cedula
    cedula = request.form.get('cedula').strip()
    client = Client.query.filter_by(cedula=cedula).first()
    
    show_client_modal = False
    if client:
        current_client_id = client.id
        return redirect(url_for('main.index'))
    else:
        temp_cedula = cedula
        show_register_modal = True
        return redirect(url_for('main.index'))

@bp.route('/show-register-form')
def show_register_form():
    global show_register_modal, show_form_register
    show_register_modal = False
    show_form_register = True
    return redirect(url_for('main.index'))

@bp.route('/save-client', methods=['POST'])
def save_client():
    global current_client_id, show_form_register, temp_cedula
    cedula = request.form.get('cedula')
    name = request.form.get('name')
    address = request.form.get('address')
    
    new_client = Client(cedula=cedula, name=name, address=address)
    db.session.add(new_client)
    db.session.commit()
    
    current_client_id = new_client.id
    show_form_register = False
    return redirect(url_for('main.index'))

@bp.route('/cancel-client')
def cancel_client():
    global show_client_modal, show_register_modal, show_form_register, show_invoice, show_client_actions_modal, temp_cedula
    show_client_modal = False
    show_register_modal = False
    show_form_register = False
    show_invoice = False
    show_client_actions_modal = False
    temp_cedula = ""
    return redirect(url_for('main.index'))

@bp.route('/cancel-register')
def cancel_register():
    global show_form_register, show_register_modal, show_client_modal, show_invoice, show_client_actions_modal, temp_cedula
    show_form_register = False
    show_register_modal = False
    show_client_modal = False
    show_invoice = False
    show_client_actions_modal = False
    temp_cedula = ""
    return redirect(url_for('main.index'))

@bp.route('/close-modal')
def close_modal():
    global modal_state, show_client_modal, show_register_modal, show_form_register, show_invoice, show_client_actions_modal
    modal_state = False
    show_client_modal = False
    show_register_modal = False
    show_form_register = False
    show_invoice = False
    show_client_actions_modal = False
    return redirect(url_for('main.index'))

@bp.route('/toggle-modal')
def toggle_modal():
    global modal_state
    modal_state = not modal_state
    return redirect(url_for('main.index'))

@bp.route('/edit/<int:id>')
def edit_product(id):
    product = Product.query.get_or_404(id)
    search_query = request.args.get('q', '').strip()
    active_cat = request.args.get('cat', 'all')
    return _render_pos_page(search_query=search_query, active_cat=active_cat, edit_product=product)

@bp.route('/update/<int:id>', methods=['POST'])
def update_product(id):
    product = Product.query.get_or_404(id)
    product.name = request.form.get('name')
    product.price = float(request.form.get('price'))
    product.stock = int(request.form.get('stock'))
    product.category = request.form.get('category')
    
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            upload_folder = os.path.join('static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            file.save(os.path.join(upload_folder, filename))
            product.image = filename

    presentations_str = request.form.get('presentations', '')
    Presentation.query.filter_by(product_id=product.id).delete()
    if presentations_str:
        pres_list = [p.strip() for p in presentations_str.split(',') if p.strip()]
        for p_name in pres_list:
            db.session.add(Presentation(name=p_name, product_id=product.id))

    db.session.commit()
    return redirect(url_for('main.index'))

@bp.route('/create-product', methods=['POST'])
def create_product():
    global modal_state
    name = request.form.get('name')
    price = float(request.form.get('price'))
    stock = int(request.form.get('stock'))
    category = request.form.get('category')
    presentations_str = request.form.get('presentations', '')

    filename = 'default.png'
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            upload_folder = os.path.join('static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            file.save(os.path.join(upload_folder, filename))

    new_prod = Product(name=name, price=price, stock=stock, category=category, image=filename)
    db.session.add(new_prod)
    db.session.commit()

    if presentations_str:
        pres_list = [p.strip() for p in presentations_str.split(',') if p.strip()]
        for p_name in pres_list:
            db.session.add(Presentation(name=p_name, product_id=new_prod.id))
        db.session.commit()

    modal_state = False
    return redirect(url_for('main.index'))

@bp.route('/add/<int:product_id>')
def add_to_cart(product_id):
    global current_client_id
    if not current_client_id:
        return redirect(url_for('main.ask_client'))
    
    product = Product.query.get_or_404(product_id)
    if product.stock > 0:
        existing = next((item for item in cart if item['id'] == product_id), None)
        if existing:
            existing['qty'] += 1
        else:
            cart.append({'id': product.id, 'name': product.name, 'price': product.price, 'qty': 1})
    return redirect(url_for('main.index'))

@bp.route('/update-qty/<int:product_id>/<action>')
def update_qty(product_id, action):
    global cart
    item = next((i for i in cart if i['id'] == product_id), None)
    if item:
        if action == 'plus':
            item['qty'] += 1
        elif action == 'minus':
            item['qty'] -= 1
            if item['qty'] <= 0:
                cart.remove(item)
        elif action == 'delete':
            cart.remove(item)
    return redirect(url_for('main.index'))

@bp.route('/checkout')
def checkout():
    if cart and current_client_id:
        session['show_payment_screen'] = True
        flash('Seleccione el método de pago para continuar.', 'info')
    return redirect(url_for('main.index'))

@bp.route('/process-payment-modal', methods=['POST'])
def process_payment_modal():
    payment_method = request.form.get('payment_method')
    try:
        amount_paid = float(request.form.get('amount_paid', 0))
    except ValueError:
        amount_paid = 0.0

    if 'payments_applied' not in session:
        session['payments_applied'] = []

    # Guardar el pago parcial o total en la lista de abonos (en Bs.)
    session['payments_applied'].append({
        'method': payment_method,
        'amount': amount_paid
    })
    session.modified = True

    total_cart = sum(item['price'] * item['qty'] for item in cart)
    total_cart_bs = total_cart * TASA_BCV
    total_paid = sum(p['amount'] for p in session['payments_applied'])

    if total_paid >= total_cart_bs:
        session['payment_simulated'] = True
        flash('¡Monto total cubierto exitosamente!', 'success')
    else:
        remaining = total_cart_bs - total_paid
        flash(f'Pago parcial de Bs. {amount_paid:.2f} registrado. Falta por cubrir Bs. {remaining:.2f}.', 'warning')

    return redirect(url_for('main.index'))

@bp.route('/finalize-sale')
def finalize_sale():
    global cart, current_client_id, show_invoice, last_sale_id, last_sale_items_cache

    if cart and current_client_id:
        total = sum(item['price'] * item['qty'] for item in cart)
        new_sale = Sale(total=total, client_id=current_client_id)
        db.session.add(new_sale)

        for item in cart:
            p = Product.query.get(item['id'])
            if p:
                p.stock -= item['qty']
        db.session.commit()

        last_sale_id = new_sale.id
        last_sale_items_cache = list(cart)
        cart.clear()
        current_client_id = None

        show_invoice = True
        session['show_invoice'] = True

    session.pop('show_payment_screen', None)
    session.pop('payment_simulated', None)
    session.pop('payments_applied', None)

    return redirect(url_for('main.index'))

@bp.route('/cancel-payment')
def cancel_payment():
    session.pop('show_payment_screen', None)
    session.pop('payment_simulated', None)
    session.pop('payments_applied', None)
    flash('Proceso de pago cancelado.', 'info')
    return redirect(url_for('main.index'))

@bp.route('/close-invoice')
def close_invoice():
    global show_invoice
    show_invoice = False
    session.pop('show_invoice', None)
    return redirect(url_for('main.index'))

@bp.route('/clear')
def clear_cart():
    cart.clear()
    session.pop('show_payment_screen', None)
    session.pop('payments_applied', None)
    session.pop('payment_simulated', None)
    return redirect(url_for('main.index'))