from flask import Flask, render_template, redirect, url_for, flash, session, request
import os
from config import AppConfig
from werkzeug.security import generate_password_hash, check_password_hash
from forms import LoginForm, RegisterForm
from flask_mysqldb import MySQL
from MySQLdb.cursors import DictCursor
from functools import wraps  # ✅ Import necesario para los decoradores
from werkzeug.utils import secure_filename # ✅ Import para subir archivos
import stripe # ✅ Import para Stripe

app = Flask(__name__)
app.config.from_object(AppConfig)

stripe.api_key = app.config.get('STRIPE_SECRET_KEY')
if not stripe.api_key or stripe.api_key == "TU_CLAVE_SECRETA_DE_STRIPE_VA_AQUI":
    print("ADVERTENCIA: La 'STRIPE_SECRET_KEY' no está configurada en config.py. El pago fallará.")
# ---------------------------------

# (NUEVO) Configuración de la carpeta de subida
UPLOAD_FOLDER_PRODUCTOS = os.path.join(app.root_path, 'static/uploads/productos')
os.makedirs(UPLOAD_FOLDER_PRODUCTOS, exist_ok=True)
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
# ---------------------------------

# ----------------------
# Conexión a la base de datos con Flask-MySQLdb
# ----------------------
mysql = MySQL(app)

# ----------------------
# Función auxiliar
# ----------------------
def user_authenticated():
    return session.get("logged_in", False)

# ----------------------
# Decoradores personalizados
# ----------------------
def login_required(f):
    """Verifica si el usuario está logueado."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("logged_in"):
            flash("Debes iniciar sesión para acceder a esta página", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def role_required(role):
    """Verifica si el usuario tiene el rol requerido."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get("rol") != role:
                flash("No tienes permiso para acceder a esta página", "error")
                return redirect(url_for("index"))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ----------------------
# Login con WTForms
# ----------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        usuario = form.usuario.data.strip()
        password = form.password.data

        cursor = mysql.connection.cursor(DictCursor)  # ✅ Usar DictCursor
        try:
            cursor.execute("SELECT * FROM regis WHERE username = %s", (usuario,))
            user = cursor.fetchone()
        finally:
            cursor.close()

        if user and check_password_hash(user["password"], password):
            session["logged_in"] = True
            session["usuario"] = usuario
            session["rol"] = user.get("rol", "usuario")
            # Limpiar carrito anterior si existía
            session.pop("carrito", None)
            flash("Has iniciado sesión correctamente", "success")
            return redirect(url_for("index"))
        else:
            flash("Usuario o contraseña incorrectos", "error")

    return render_template("login.html", form=form, user_authenticated=user_authenticated())
4
# ----------------------
# Registro con WTForms
# ----------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        usrname = form.usrname.data.strip()
        usrln = form.usrln.data.strip()
        usrn = form.usrn.data.strip()
        usrmail = form.usrmail.data.strip()
        usrpass = form.usrpass.data

        cursor = mysql.connection.cursor()
        try:
            cursor.execute(
                "INSERT INTO regis (nombre, apellidos, username, email, password, rol) VALUES (%s, %s, %s, %s, %s, %s)",
                (usrname, usrln, usrn, usrmail, generate_password_hash(usrpass), "usuario")
            )
            mysql.connection.commit()
            flash("Registro exitoso", "success")
            return redirect(url_for("login"))
        except Exception:  # Usuario o correo duplicado
            flash("El usuario o correo ya existe", "error")
        finally:
            cursor.close()

    return render_template("forms/register.html", form=form, user_authenticated=user_authenticated())

# ----------------------
# Logout
# ----------------------
@app.route('/logout')
@login_required  # ✅ Solo usuarios logueados pueden cerrar sesión
def logout():
    session.pop("logged_in", None)
    session.pop("usuario", None)
    session.pop("rol", None)
    session.pop("carrito", None) # Limpiar carrito al salir
    flash("Has cerrado sesión")
    return redirect(url_for('index'))

# ----------------------
# Página principal
# ----------------------
@app.route('/')
def index():
    return render_template('index.html', user_authenticated=user_authenticated(), fondo="Fondo.gif")

# ----------------------
# Página de juegos (Galería)
# ----------------------
@app.route('/juegos')
def juegos():
    # Esta ruta ahora muestra la galería de juegos
    return render_template('juegos.html', user_authenticated=user_authenticated())

# ----------------------
# Página de juego (Individual)
# ----------------------
@app.route("/juego/<nombre>")
def juego(nombre):
    fondos = {
        "half-life": "FondoHL.jpg", "cs": "FondoCS.jpg", "portal": "FondoPortal.jpg",
        "tf2": "FondoTF2.jpg", "l4d": "FondoL4D.jpg", "l4d2": "FondoL4D2.jpg",
        "dota2": "FondoDota2.jpg", "alyx": "FondoAlyx.jpg"
    }
    fondo = fondos.get(nombre, "Fondo.gif")
    
    # Lógica para juegos protegidos
    juegos_protegidos = ['l4d', 'l4d2', 'dota2', 'alyx']
    if nombre in juegos_protegidos and not user_authenticated():
        flash("Debes iniciar sesión para ver este contenido", "error")
        return redirect(url_for('login'))

    juego_data = {"nombre": nombre, "titulo": nombre.replace('-', ' ').capitalize(), "descripcion": "Descripción..."}
    return render_template("juego.html", juego=juego_data, fondo=fondo, user_authenticated=user_authenticated())

# ----------------------
# Subida de archivos (Multimedia)
# ----------------------
@app.route('/upload', methods=['GET', 'POST'])
@login_required  # ✅ Solo usuarios logueados pueden subir archivos
def upload():
    cursor = mysql.connection.cursor(DictCursor)
    try:
        if request.method == 'POST':
            if "archivo" not in request.files:
                flash("No se seleccionó archivo", "error")
                return redirect(request.url)

            file = request.files["archivo"]
            if file.filename == "":
                flash("Nombre de archivo vacío", "error")
                return redirect(request.url)

            # (MODIFICADO) Carpeta de subida 'uploads' (general)
            upload_folder = os.path.join(app.root_path, "static/uploads")
            os.makedirs(upload_folder, exist_ok=True)
            
            # Usar secure_filename para seguridad
            filename = secure_filename(file.filename)
            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)

            tipo = "video" if filename.lower().endswith((".mp4", ".mov", ".avi")) else "imagen"
            usuario = session.get("usuario")
            # (MODIFICADO) Guardar solo la ruta relativa
            ruta_relativa = f"uploads/{filename}" 

            cursor.execute(
                "INSERT INTO multimedia (tipo, nombre, ruta, usuario) VALUES (%s, %s, %s, %s)",
                (tipo, filename, ruta_relativa, usuario)
            )
            mysql.connection.commit()

            flash("Archivo subido correctamente", "success")
            return redirect(url_for("upload"))

        cursor.execute("SELECT id, tipo, nombre, ruta, usuario, fecha FROM multimedia ORDER BY fecha DESC")
        multimedia = cursor.fetchall()
    finally:
        cursor.close()

    # (CORREGIDO) Se quitó el prefijo 'templates/'
    return render_template("upload.html", multimedia=multimedia, user_authenticated=user_authenticated())

# ----------------------
# Comentarios
# ----------------------
@app.route("/comentarios", methods=["GET", "POST"])
@login_required  # ✅ Solo usuarios logueados pueden comentar
def comentarios():
    cursor = mysql.connection.cursor(DictCursor)
    try:
        if request.method == "POST":
            texto = request.form["comentario"]
            usuario = session.get("usuario")

            cursor.execute(
                "INSERT INTO comentarios (username, comentario) VALUES (%s, %s)",
                (usuario, texto)
            )
            mysql.connection.commit()
            flash("Comentario publicado", "success")
            return redirect(url_for("comentarios"))

        cursor.execute("SELECT id, username, comentario, fecha FROM comentarios ORDER BY fecha DESC")
        comentarios_db = cursor.fetchall()
    finally:
        cursor.close()

    # (CORREGIDO) Se quitó el prefijo 'templates/'
    return render_template("comentarios.html", comentarios=comentarios_db, user_authenticated=user_authenticated())


# ==================================================================
# RUTAS DE LA TIENDA Y PANEL DE ADMIN
# ==================================================================

# ----------------------
# TIENDA - Catálogo de Productos (Público)
# ----------------------
@app.route('/tienda')
def tienda():
    cursor = mysql.connection.cursor(DictCursor)
    try:
        cursor.execute("SELECT * FROM productos WHERE stock > 0")
        productos = cursor.fetchall()
    finally:
        cursor.close()
    # (CORREGIDO) Se quitó el prefijo 'templates/'
    return render_template('tienda.html', productos=productos, user_authenticated=user_authenticated())

# ----------------------
# TIENDA - Panel de Admin (Admin)
# ----------------------
@app.route('/admin/productos', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_productos():
    cursor = mysql.connection.cursor(DictCursor)
    
    # Lógica para AGREGAR producto
    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = request.form['precio']
        stock = request.form['stock']
        
        imagen_url_relativa = None # Default a None

        # (NUEVO) Lógica para subir imagen
        if 'imagen_file' in request.files:
            file = request.files['imagen_file']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(UPLOAD_FOLDER_PRODUCTOS, filename)
                file.save(filepath)
                imagen_url_relativa = f"uploads/productos/{filename}" # Ruta relativa para la BD

        try:
            cursor.execute(
                "INSERT INTO productos (nombre, descripcion, precio, stock, imagen_url) VALUES (%s, %s, %s, %s, %s)",
                (nombre, descripcion, precio, stock, imagen_url_relativa)
            )
            mysql.connection.commit()
            flash('Producto agregado correctamente', 'success')
        except Exception as e:
            flash(f'Error al agregar producto: {str(e)}', 'error')
        
        return redirect(url_for('admin_productos'))

    # Lógica para LEER (GET)
    try:
        cursor.execute("SELECT * FROM productos ORDER BY id DESC")
        productos = cursor.fetchall()
    finally:
        cursor.close()
        
    # (CORREGIDO) Se quitó el prefijo 'templates/'
    return render_template('admin_productos.html', productos=productos, user_authenticated=user_authenticated())

# ----------------------
# TIENDA - Modificar Producto (Admin)
# ----------------------
@app.route('/admin/productos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def modificar_producto(id):
    cursor = mysql.connection.cursor(DictCursor)
    
    # Lógica para ACTUALIZAR (POST)
    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = request.form['precio']
        stock = request.form['stock']
        imagen_url_relativa = request.form['imagen_actual'] # Mantiene la imagen actual por defecto

        # (NUEVO) Lógica para REEMPLAZAR imagen
        if 'imagen_file' in request.files:
            file = request.files['imagen_file']
            if file and file.filename != '' and allowed_file(file.filename):
                # (Opcional: borrar imagen antigua del servidor)
                # ... (agregar lógica para borrar os.path.join(app.root_path, 'static', imagen_url_relativa))
                
                filename = secure_filename(file.filename)
                filepath = os.path.join(UPLOAD_FOLDER_PRODUCTOS, filename)
                file.save(filepath)
                imagen_url_relativa = f"uploads/productos/{filename}" # Nueva ruta

        try:
            cursor.execute("""
                UPDATE productos 
                SET nombre=%s, descripcion=%s, precio=%s, stock=%s, imagen_url=%s 
                WHERE id=%s
            """, (nombre, descripcion, precio, stock, imagen_url_relativa, id))
            mysql.connection.commit()
            flash('Producto actualizado correctamente', 'success')
        except Exception as e:
            flash(f'Error al actualizar producto: {str(e)}', 'error')
        finally:
            cursor.close()

        return redirect(url_for('admin_productos'))

    # Lógica para LEER (GET)
    try:
        cursor.execute("SELECT * FROM productos WHERE id = %s", (id,))
        producto = cursor.fetchone()
    finally:
        cursor.close()

    if not producto:
        flash('Producto no encontrado', 'error')
        return redirect(url_for('admin_productos'))
        
    # (CORREGIDO) Se quitó el prefijo 'templates/'
    return render_template('modificar_producto.html', producto=producto, user_authenticated=user_authenticated())

# ----------------------
# TIENDA - Eliminar Producto (Admin)
# ----------------------
@app.route('/admin/productos/eliminar/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def eliminar_producto(id):
    cursor = mysql.connection.cursor(DictCursor) # Usar DictCursor
    try:
        # (NUEVO) Opcional: borrar imagen del servidor antes de borrar de la BD
        cursor.execute("SELECT imagen_url FROM productos WHERE id = %s", (id,))
        producto = cursor.fetchone()
        if producto and producto['imagen_url']:
            filepath = os.path.join(app.root_path, 'static', producto['imagen_url'])
            if os.path.isfile(filepath):
                os.remove(filepath)
        
        cursor.execute("DELETE FROM productos WHERE id = %s", (id,))
        mysql.connection.commit()
        flash('Producto eliminado correctamente', 'success')
    except Exception as e:
        flash(f'Error al eliminar producto: {str(e)}', 'error')
    finally:
        cursor.close()
    
    return redirect(url_for('admin_productos'))


# ==================================================================
# RUTAS DEL CARRITO DE COMPRAS
# ==================================================================

# ----------------------
# CARRITO - Agregar Producto (Usuario Logueado)
# ----------------------
@app.route('/carrito/agregar/<int:id>', methods=['POST'])
@login_required
def agregar_al_carrito(id):
    # Inicializar carrito en la sesión si no existe
    if 'carrito' not in session:
        session['carrito'] = {}

    carrito = session['carrito']
    producto_id = str(id) # Usar strings para las claves del diccionario de sesión
    
    # Obtener cantidad del formulario, default a 1
    try:
        cantidad = int(request.form.get('cantidad', 1))
        if cantidad < 1:
            cantidad = 1
    except ValueError:
        cantidad = 1

    # (NUEVO) Verificar stock antes de agregar
    cursor = mysql.connection.cursor(DictCursor)
    cursor.execute("SELECT stock FROM productos WHERE id = %s", (producto_id,))
    producto = cursor.fetchone()
    cursor.close()

    stock_disponible = producto['stock'] if producto else 0
    cantidad_en_carrito = carrito.get(producto_id, 0)
    
    if (cantidad + cantidad_en_carrito) > stock_disponible:
        flash(f'No hay suficiente stock. Solo quedan {stock_disponible} disponibles.', 'error')
        return redirect(url_for('tienda'))
    # --- Fin verificación de stock ---

    # Agregar o actualizar cantidad
    if producto_id in carrito:
        carrito[producto_id] += cantidad
    else:
        carrito[producto_id] = cantidad
    
    session.modified = True  # Marcar la sesión como modificada
    flash(f'Producto agregado al carrito (Cantidad: {cantidad})', 'success')
    
    # Redirigir de vuelta a la tienda
    return redirect(url_for('tienda'))

# ----------------------
# CARRITO - Ver Carrito (Usuario Logueado)
# ----------------------
@app.route('/carrito')
@login_required
def ver_carrito():
    if 'carrito' not in session or not session['carrito']:
        # (CORREGIDO) Se quitó el prefijo 'templates/'
        return render_template('carrito.html', items_en_carrito=[], total=0, user_authenticated=user_authenticated())

    carrito = session['carrito']
    ids_productos = list(carrito.keys())
    
    if not ids_productos:
         # (CORREGIDO) Se quitó el prefijo 'templates/'
         return render_template('carrito.html', items_en_carrito=[], total=0, user_authenticated=user_authenticated())

    # Crear un string de placeholders (%s, %s, %s)
    placeholders = ', '.join(['%s'] * len(ids_productos))
    
    cursor = mysql.connection.cursor(DictCursor)
    try:
        # Obtener detalles de todos los productos en el carrito
        cursor.execute(f"SELECT * FROM productos WHERE id IN ({placeholders})", tuple(ids_productos))
        productos = cursor.fetchall()
    finally:
        cursor.close()

    items_en_carrito = []
    total = 0
    
    for producto in productos:
        producto_id = str(producto['id'])
        cantidad = carrito.get(producto_id, 0) # Usar .get para seguridad
        
        if cantidad > 0:
            # (NUEVO) Verificar si la cantidad en carrito supera el stock actual
            if cantidad > producto['stock']:
                cantidad = producto['stock'] # Ajustar cantidad al stock disponible
                session['carrito'][producto_id] = cantidad # Actualizar sesión
                flash(f"Se ajustó la cantidad de '{producto['nombre']}' al stock disponible ({cantidad})", "warning")
            
            subtotal = producto['precio'] * cantidad
            
            items_en_carrito.append({
                'id': producto['id'],
                'nombre': producto['nombre'],
                'precio': producto['precio'],
                'cantidad': cantidad,
                'subtotal': subtotal,
                'imagen_url': producto['imagen_url'] # Pasamos la ruta de la BD
            })
            total += subtotal

    session.modified = True
    # (CORREGIDO) Se quitó el prefijo 'templates/'
    return render_template('carrito.html', items_en_carrito=items_en_carrito, total=total, user_authenticated=user_authenticated())

# ----------------------
# CARRITO - Eliminar Producto (Usuario Logueado)
# ----------------------
@app.route('/carrito/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_del_carrito(id):
    producto_id = str(id)
    if 'carrito' in session and producto_id in session['carrito']:
        session['carrito'].pop(producto_id)
        session.modified = True
        flash('Producto eliminado del carrito', 'success')
    else:
        flash('El producto no estaba en el carrito', 'error')

    return redirect(url_for('ver_carrito'))


# ==================================================================
# (NUEVO) RUTAS DE PAGO CON STRIPE
# ==================================================================

@app.route('/crear-sesion-checkout', methods=['POST'])
@login_required
def crear_sesion_checkout():
    # 1. Obtener el carrito de la sesión
    if 'carrito' not in session or not session['carrito']:
        flash("Tu carrito está vacío.", "error")
        return redirect(url_for('ver_carrito'))

    carrito = session['carrito']
    ids_productos = list(carrito.keys())
    
    if not ids_productos:
        flash("Tu carrito está vacío.", "error")
        return redirect(url_for('ver_carrito'))

    # 2. Obtener los detalles de los productos desde la BD
    placeholders = ', '.join(['%s'] * len(ids_productos))
    cursor = mysql.connection.cursor(DictCursor)
    cursor.execute(f"SELECT id, nombre, precio, stock FROM productos WHERE id IN ({placeholders})", tuple(ids_productos))
    productos = cursor.fetchall()
    cursor.close()

    # 3. Crear la lista 'line_items' para Stripe
    line_items = []
    productos_fuera_de_stock = []

    for producto in productos:
        producto_id = str(producto['id'])
        cantidad = carrito.get(producto_id, 0)

        # 4. (IMPORTANTE) Doble verificación de stock
        if cantidad > producto['stock']:
            productos_fuera_de_stock.append(producto['nombre'])
        
        if cantidad > 0:
            line_items.append({
                'price_data': {
                    'currency': 'mxn', # Cambia a tu moneda (ej: 'usd')
                    'product_data': {
                        'name': producto['nombre'],
                    },
                    # ¡¡Stripe usa centavos!!
                    'unit_amount': int(producto['precio'] * 100), 
                },
                'quantity': cantidad,
            })

    # 5. Si algo falló en la verificación de stock, regresar
    if productos_fuera_de_stock:
        flash(f"Error: Los siguientes productos ya no tienen stock suficiente: {', '.join(productos_fuera_de_stock)}", "error")
        return redirect(url_for('ver_carrito'))

    if not line_items:
        flash("Error al procesar el carrito.", "error")
        return redirect(url_for('ver_carrito'))

    # 6. Crear la sesión de Stripe Checkout
    try:
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            # ¡IMPORTANTE! Asegúrate de que estas rutas existan
            success_url=url_for('pedido_exitoso', _external=True),
            cancel_url=url_for('pedido_cancelado', _external=True),
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        flash(f"Error al contactar al servicio de pago: {str(e)}", "error")
        return redirect(url_for('ver_carrito'))

# ----------------------
# PÁGINAS DE RETORNO DE STRIPE
# ----------------------
@app.route('/pedido-exitoso')
@login_required
def pedido_exitoso():
    # (NUEVO) Lógica para descontar stock después de una compra exitosa
    if 'carrito' in session and session['carrito']:
        carrito = session['carrito']
        cursor = mysql.connection.cursor()
        try:
            for producto_id, cantidad in carrito.items():
                cursor.execute("UPDATE productos SET stock = stock - %s WHERE id = %s AND stock >= %s", 
                               (cantidad, producto_id, cantidad))
            mysql.connection.commit()
            # Limpiar carrito DESPUÉS de actualizar la BD
            session.pop('carrito', None)
            flash("¡Gracias por tu compra!", "success")
        except Exception as e:
            mysql.connection.rollback()
            flash(f"Error al actualizar el stock: {str(e)}", "error")
        finally:
            cursor.close()
    
    # (CORREGIDO) Se quitó el prefijo 'templates/'
    return render_template('pedido_exitoso.html', user_authenticated=user_authenticated())

@app.route('/pedido-cancelado')
@login_required
def pedido_cancelado():
    flash("El pago fue cancelado. Puedes intentarlo de nuevo.", "error")
    # (CORREGIDO) Se quitó el prefijo 'templates/'
    return render_template('pedido_cancelado.html', user_authenticated=user_authenticated())


# ==================================================================
# Borradores y Gestión de Usuarios
# ==================================================================
@app.route("/borrar_imagen/<int:id>", methods=["POST"])
@login_required
@role_required("admin")  # ✅ Solo admin puede borrar
def borrar_imagen(id):
    cursor = mysql.connection.cursor(DictCursor)
    try:
        cursor.execute("SELECT ruta FROM multimedia WHERE id = %s", (id,))
        img = cursor.fetchone()

        if img and img.get("ruta"):
            filepath = os.path.join(app.root_path, "static", img["ruta"])
            if os.path.isfile(filepath):
                os.remove(filepath)

            cursor.execute("DELETE FROM multimedia WHERE id = %s", (id,))
            mysql.connection.commit()
            flash("Imagen eliminada correctamente", "success")
        else:
            flash("Imagen no encontrada o ruta inválida", "warning")
    except Exception as e:
        flash(f"Error al eliminar la imagen: {str(e)}", "error")
    finally:
        cursor.close()

    return redirect(url_for("upload"))

# ----------------------
# Borrar comentario (solo admin)
# ----------------------
@app.route("/borrar_comentario/<int:id>", methods=["POST"])
@login_required
@role_required("admin")  # ✅ Solo admin puede borrar
def borrar_comentario(id):
    cursor = mysql.connection.cursor(DictCursor)
    try:
        cursor.execute("DELETE FROM comentarios WHERE id = %s", (id,))
        mysql.connection.commit()
        flash("Comentario eliminado", "success")
    finally:
        cursor.close()

    return redirect(url_for("comentarios"))

# ----------------------
# Gestión de usuarios (solo admin)
# ----------------------
@app.route("/usuarios")
@login_required
@role_required("admin")  # ✅ Solo admin puede acceder
def usuarios():
    cursor = mysql.connection.cursor(DictCursor)
    try:
        cursor.execute("SELECT id, nombre, apellidos, username, email, rol FROM regis")
        usuarios = cursor.fetchall()
    finally:
        cursor.close()

    # (CORREGIDO) Se quitó el prefijo 'templates/'
    return render_template("usuarios.html", usuarios=usuarios, user_authenticated=user_authenticated())

@app.route("/eliminar_usuario/<int:id>", methods=["POST"])
@login_required
@role_required("admin")
def eliminar_usuario(id):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("DELETE FROM regis WHERE id = %s", (id,))
        mysql.connection.commit()
        flash("Usuario eliminado correctamente", "success")
    finally:
        cursor.close()

    return redirect(url_for("usuarios"))

@app.route("/modificar_usuario/<int:id>", methods=["GET", "POST"])
@login_required
@role_required("admin")
def modificar_usuario(id):
    cursor = mysql.connection.cursor(DictCursor)
    try:
        if request.method == "POST":
            nombre = request.form["nombre"]
            apellidos = request.form["apellidos"]
            email = request.form["email"]
            rol = request.form["rol"]

            cursor.execute("""
                UPDATE regis SET nombre=%s, apellidos=%s, email=%s, rol=%s WHERE id=%s
            """, (nombre, apellidos, email, rol, id))
            mysql.connection.commit()
            flash("Usuario modificado correctamente", "success")
            return redirect(url_for("usuarios"))

        cursor.execute("SELECT id, nombre, apellidos, username, email, rol FROM regis WHERE id = %s", (id,))
        usuario = cursor.fetchone()
    finally:
        cursor.close()
        
    if not usuario:
        flash("Usuario no encontrado", "error")
        return redirect(url_for('usuarios'))

    # (CORREGIDO) Se quitó el prefijo 'templates/'
    return render_template("modificar_usuario.html", usuario=usuario, user_authenticated=user_authenticated())