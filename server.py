from flask import Flask, render_template, redirect, url_for, flash, session, request
import os
from config import AppConfig
from werkzeug.security import generate_password_hash, check_password_hash
from forms import LoginForm, RegisterForm
from flask_mysqldb import MySQL
from MySQLdb.cursors import DictCursor
from functools import wraps
from werkzeug.utils import secure_filename
import stripe

app = Flask(__name__)
app.config.from_object(AppConfig)

# --- Configuración de Stripe ---
# La clave se lee desde config.py para seguridad
stripe.api_key = app.config.get('STRIPE_SECRET_KEY')

# --- Configuración de Subidas ---
UPLOAD_FOLDER_PRODUCTOS = os.path.join(app.root_path, 'static/uploads/productos')
UPLOAD_FOLDER_GENERAL = os.path.join(app.root_path, 'static/uploads')
os.makedirs(UPLOAD_FOLDER_PRODUCTOS, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_GENERAL, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Base de Datos ---
mysql = MySQL(app)

# --- Decoradores y Ayudas ---
def user_authenticated():
    return session.get("logged_in", False)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            flash("Debes iniciar sesión para acceder a esta página", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get("rol") != role:
                flash("No tienes permiso para acceder a esta página", "error")
                return redirect(url_for("index"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ==================================================================
# RUTAS GENERALES (Auth, Home, Wiki)
# ==================================================================

@app.route('/')
def index():
    return render_template('index.html', user_authenticated=user_authenticated(), fondo="Fondo.gif")

@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        usuario = form.usuario.data.strip()
        password = form.password.data
        cursor = mysql.connection.cursor(DictCursor)
        try:
            cursor.execute("SELECT * FROM regis WHERE username = %s", (usuario,))
            user = cursor.fetchone()
        finally:
            cursor.close()
        
        if user and check_password_hash(user["password"], password):
            session["logged_in"] = True
            session["usuario"] = usuario
            session["rol"] = user.get("rol", "usuario")
            session.pop("carrito", None) # Limpiar carrito anterior
            flash("Has iniciado sesión correctamente", "success")
            return redirect(url_for("index"))
        else:
            flash("Usuario o contraseña incorrectos", "error")
    return render_template("login.html", form=form, user_authenticated=user_authenticated())

@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("INSERT INTO regis (nombre, apellidos, username, email, password, rol) VALUES (%s, %s, %s, %s, %s, %s)",
                (form.usrname.data.strip(), form.usrln.data.strip(), form.usrn.data.strip(), form.usrmail.data.strip(), generate_password_hash(form.usrpass.data), "usuario"))
            mysql.connection.commit()
            cursor.close()
            flash("Registro exitoso", "success")
            return redirect(url_for("login"))
        except Exception:
            flash("El usuario o correo ya existe", "error")
    return render_template("forms/register.html", form=form, user_authenticated=user_authenticated())

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash("Has cerrado sesión", "success")
    return redirect(url_for('index'))

# --- WIKI / JUEGOS ---
@app.route('/juegos')
def juegos():
    return render_template('juegos.html', user_authenticated=user_authenticated())

@app.route("/juego/<nombre>")
def juego(nombre):
    fondos = {
        "half-life": "FondoHL.jpg", "cs": "FondoCS.jpg", "portal": "FondoPortal.jpg",
        "tf2": "FondoTF2.jpg", "l4d": "FondoL4D.jpg", "l4d2": "FondoL4D2.jpg",
        "dota2": "FondoDota2.jpg", "alyx": "FondoAlyx.jpg"
    }
    fondo = fondos.get(nombre, "Fondo.gif")
    
    juegos_protegidos = ['l4d', 'l4d2', 'dota2', 'alyx']
    if nombre in juegos_protegidos and not user_authenticated():
        flash("Debes iniciar sesión para ver este contenido", "error")
        return redirect(url_for('login'))

    juego_data = {"nombre": nombre, "titulo": nombre.replace('-', ' ').capitalize(), "descripcion": "Descripción..."}
    return render_template("juego.html", juego=juego_data, fondo=fondo, user_authenticated=user_authenticated())

# ==================================================================
# RUTAS DE TIENDA Y ADMIN DE PRODUCTOS
# ==================================================================

@app.route('/tienda')
def tienda():
    cursor = mysql.connection.cursor(DictCursor)
    try:
        cursor.execute("SELECT * FROM productos WHERE stock > 0")
        productos = cursor.fetchall()
    finally:
        cursor.close()
    return render_template('tienda.html', productos=productos, user_authenticated=user_authenticated())

@app.route('/admin/productos', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_productos():
    cursor = mysql.connection.cursor(DictCursor)
    if request.method == 'POST':
        imagen_url_relativa = None
        if 'imagen_file' in request.files:
            file = request.files['imagen_file']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER_PRODUCTOS, filename))
                imagen_url_relativa = f"uploads/productos/{filename}"

        try:
            cursor.execute("INSERT INTO productos (nombre, descripcion, precio, stock, imagen_url) VALUES (%s, %s, %s, %s, %s)",
                (request.form['nombre'], request.form['descripcion'], request.form['precio'], request.form['stock'], imagen_url_relativa))
            mysql.connection.commit()
            flash('Producto agregado', 'success')
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('admin_productos'))

    cursor.execute("SELECT * FROM productos ORDER BY id DESC")
    productos = cursor.fetchall()
    cursor.close()
    return render_template('admin_productos.html', productos=productos, user_authenticated=user_authenticated())

@app.route('/admin/productos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def modificar_producto(id):
    cursor = mysql.connection.cursor(DictCursor)
    if request.method == 'POST':
        imagen_url = request.form['imagen_actual']
        if 'imagen_file' in request.files:
            file = request.files['imagen_file']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(UPLOAD_FOLDER_PRODUCTOS, filename))
                imagen_url = f"uploads/productos/{filename}"

        try:
            cursor.execute("UPDATE productos SET nombre=%s, descripcion=%s, precio=%s, stock=%s, imagen_url=%s WHERE id=%s",
                (request.form['nombre'], request.form['descripcion'], request.form['precio'], request.form['stock'], imagen_url, id))
            mysql.connection.commit()
            flash('Producto actualizado', 'success')
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('admin_productos'))

    cursor.execute("SELECT * FROM productos WHERE id = %s", (id,))
    producto = cursor.fetchone()
    cursor.close()
    return render_template('modificar_producto.html', producto=producto, user_authenticated=user_authenticated())

@app.route('/admin/productos/eliminar/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def eliminar_producto(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM productos WHERE id = %s", (id,))
    mysql.connection.commit()
    cursor.close()
    flash('Producto eliminado', 'success')
    return redirect(url_for('admin_productos'))

# ==================================================================
# RUTAS DE CARRITO Y PAGO
# ==================================================================

@app.route('/carrito/agregar/<int:id>', methods=['POST'])
@login_required
def agregar_al_carrito(id):
    if 'carrito' not in session: session['carrito'] = {}
    carrito = session['carrito']
    pid = str(id)
    cant = int(request.form.get('cantidad', 1))
    
    # Validar stock
    cursor = mysql.connection.cursor(DictCursor)
    cursor.execute("SELECT stock FROM productos WHERE id = %s", (pid,))
    prod = cursor.fetchone()
    cursor.close()
    
    if prod and (carrito.get(pid, 0) + cant) <= prod['stock']:
        carrito[pid] = carrito.get(pid, 0) + cant
        session.modified = True
        flash('Agregado al carrito', 'success')
    else:
        flash('No hay suficiente stock', 'error')
    return redirect(url_for('tienda'))

@app.route('/carrito')
@login_required
def ver_carrito():
    carrito = session.get('carrito', {})
    ids = list(carrito.keys())
    items = []
    total = 0
    
    if ids:
        cursor = mysql.connection.cursor(DictCursor)
        format_strings = ','.join(['%s'] * len(ids))
        cursor.execute(f"SELECT * FROM productos WHERE id IN ({format_strings})", tuple(ids))
        productos = cursor.fetchall()
        cursor.close()
        
        for p in productos:
            pid = str(p['id'])
            c = carrito.get(pid, 0)
            if c > 0:
                sub = p['precio'] * c
                items.append({**p, 'cantidad': c, 'subtotal': sub})
                total += sub
    
    return render_template('carrito.html', items_en_carrito=items, total=total, user_authenticated=user_authenticated())

@app.route('/carrito/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_del_carrito(id):
    pid = str(id)
    if 'carrito' in session and pid in session['carrito']:
        session['carrito'].pop(pid)
        session.modified = True
        flash('Eliminado del carrito', 'success')
    return redirect(url_for('ver_carrito'))

@app.route('/crear-sesion-checkout', methods=['POST'])
@login_required
def crear_sesion_checkout():
    carrito = session.get('carrito', {})
    if not carrito: return redirect(url_for('ver_carrito'))
    
    ids = list(carrito.keys())
    cursor = mysql.connection.cursor(DictCursor)
    format_strings = ','.join(['%s'] * len(ids))
    cursor.execute(f"SELECT id, nombre, precio FROM productos WHERE id IN ({format_strings})", tuple(ids))
    productos_db = cursor.fetchall()
    cursor.close()

    line_items = []
    for p in productos_db:
        c = carrito.get(str(p['id']), 0)
        if c > 0:
            line_items.append({
                'price_data': {
                    'currency': 'mxn',
                    'product_data': {'name': p['nombre']},
                    'unit_amount': int(p['precio'] * 100),
                },
                'quantity': c,
            })
            
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=url_for('pedido_exitoso', _external=True),
            cancel_url=url_for('pedido_cancelado', _external=True),
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        flash(f"Error Stripe: {str(e)}", "error")
        return redirect(url_for('ver_carrito'))

@app.route('/pedido-exitoso')
@login_required
def pedido_exitoso():
    carrito = session.get('carrito', {})
    if carrito:
        cursor = mysql.connection.cursor()
        for pid, cant in carrito.items():
            cursor.execute("UPDATE productos SET stock = stock - %s WHERE id = %s", (cant, pid))
        mysql.connection.commit()
        cursor.close()
        session.pop('carrito', None)
    return render_template('pedido_exitoso.html', user_authenticated=user_authenticated())

@app.route('/pedido-cancelado')
@login_required
def pedido_cancelado():
    return render_template('pedido_cancelado.html', user_authenticated=user_authenticated())

# ==================================================================
# MULTIMEDIA Y COMENTARIOS
# ==================================================================

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    cursor = mysql.connection.cursor(DictCursor)
    if request.method == 'POST':
        if 'archivo' not in request.files: return redirect(request.url)
        file = request.files['archivo']
        if file.filename == '': return redirect(request.url)
        
        filename = secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_FOLDER_GENERAL, filename))
        tipo = "video" if filename.lower().endswith(('.mp4', '.mov')) else "imagen"
        
        cursor.execute("INSERT INTO multimedia (tipo, nombre, ruta, usuario) VALUES (%s, %s, %s, %s)",
            (tipo, filename, f"uploads/{filename}", session.get("usuario")))
        mysql.connection.commit()
        flash("Archivo subido", "success")
        return redirect(url_for('upload'))

    cursor.execute("SELECT * FROM multimedia ORDER BY id DESC")
    multimedia = cursor.fetchall()
    cursor.close()
    return render_template("upload.html", multimedia=multimedia, user_authenticated=user_authenticated())

@app.route("/borrar_imagen/<int:id>", methods=["POST"])
@login_required
@role_required("admin")
def borrar_imagen(id):
    cursor = mysql.connection.cursor(DictCursor)
    cursor.execute("SELECT ruta FROM multimedia WHERE id = %s", (id,))
    img = cursor.fetchone()
    if img:
        path = os.path.join(app.root_path, 'static', img['ruta'])
        if os.path.exists(path): os.remove(path)
        cursor.execute("DELETE FROM multimedia WHERE id = %s", (id,))
        mysql.connection.commit()
        flash("Eliminado", "success")
    cursor.close()
    return redirect(url_for("upload"))

@app.route("/comentarios", methods=["GET", "POST"])
@login_required
def comentarios():
    cursor = mysql.connection.cursor(DictCursor)
    if request.method == "POST":
        cursor.execute("INSERT INTO comentarios (username, comentario) VALUES (%s, %s)",
            (session.get("usuario"), request.form["comentario"]))
        mysql.connection.commit()
        flash("Comentario publicado", "success")
        return redirect(url_for("comentarios"))

    cursor.execute("SELECT * FROM comentarios ORDER BY fecha DESC")
    comentarios_db = cursor.fetchall()
    cursor.close()
    return render_template("comentarios.html", comentarios=comentarios_db, user_authenticated=user_authenticated())

@app.route("/borrar_comentario/<int:id>", methods=["POST"])
@login_required
@role_required("admin")
def borrar_comentario(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM comentarios WHERE id = %s", (id,))
    mysql.connection.commit()
    cursor.close()
    flash("Comentario eliminado", "success")
    return redirect(url_for("comentarios"))

# ==================================================================
# GESTIÓN DE USUARIOS (ADMIN)
# ==================================================================

@app.route("/usuarios")
@login_required
@role_required("admin")
def usuarios():
    cursor = mysql.connection.cursor(DictCursor)
    cursor.execute("SELECT * FROM regis")
    usuarios = cursor.fetchall()
    cursor.close()
    return render_template("usuarios.html", usuarios=usuarios, user_authenticated=user_authenticated())

@app.route("/eliminar_usuario/<int:id>", methods=["POST"])
@login_required
@role_required("admin")
def eliminar_usuario(id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM regis WHERE id = %s", (id,))
    mysql.connection.commit()
    flash("Usuario eliminado", "success")
    cursor.close()
    return redirect(url_for("usuarios"))

@app.route("/modificar_usuario/<int:id>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def modificar_usuario(id):
    cursor = mysql.connection.cursor(DictCursor)
    try:
        if request.method == "POST":
            cursor.execute("UPDATE regis SET nombre=%s, apellidos=%s, email=%s, rol=%s WHERE id=%s",
                (request.form["nombre"], request.form["apellidos"], request.form["email"], request.form["rol"], id))
            mysql.connection.commit()
            flash("Usuario modificado", "success")
            return redirect(url_for("usuarios"))

        cursor.execute("SELECT * FROM regis WHERE id = %s", (id,))
        usuario = cursor.fetchone()
        
        if not usuario:
            flash("Usuario no encontrado", "error")
            return redirect(url_for('usuarios'))

        return render_template("modificar_usuario.html", usuario=usuario, user_authenticated=user_authenticated())
    finally:
        cursor.close()