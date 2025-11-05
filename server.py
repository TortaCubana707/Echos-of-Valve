from flask import Flask, render_template, redirect, url_for, flash, session, request
import os
from config import AppConfig
from werkzeug.security import generate_password_hash, check_password_hash
# ✅ IMPORTACIÓN NECESARIA
from werkzeug.utils import secure_filename
from forms import LoginForm, RegisterForm
from flask_mysqldb import MySQL
from MySQLdb.cursors import DictCursor
from functools import wraps

app = Flask(__name__)
app.config.from_object(AppConfig)

# ----------------------
# Conexión a la base de datos
# ----------------------
mysql = MySQL(app)

# ✅ CONFIGURACIÓN: Carpeta para subir imágenes de productos
app.config['PRODUCT_UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/uploads/productos')
os.makedirs(app.config['PRODUCT_UPLOAD_FOLDER'], exist_ok=True)


# ----------------------
# Función auxiliar
# ----------------------
def user_authenticated():
    return session.get("logged_in", False)

# ----------------------
# Decoradores
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
# Login
# ----------------------
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
            session.pop("carrito", None)
            flash("Has iniciado sesión correctamente", "success")
            return redirect(url_for("index"))
        else:
            flash("Usuario o contraseña incorrectos", "error")

    return render_template("login.html", form=form, user_authenticated=user_authenticated())

# ----------------------
# Registro
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
        except Exception:
            flash("El usuario o correo ya existe", "error")
        finally:
            cursor.close()

    return render_template("forms/register.html", form=form, user_authenticated=user_authenticated())

# ----------------------
# Logout
# ----------------------
@app.route('/logout')
@login_required
def logout():
    session.pop("logged_in", None)
    session.pop("usuario", None)
    session.pop("rol", None)
    session.pop("carrito", None)
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
@login_required
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

            # Esta es la carpeta para 'multimedia', no para 'productos'
            upload_folder = os.path.join(app.root_path, "static/uploads")
            os.makedirs(upload_folder, exist_ok=True)

            filepath = os.path.join(upload_folder, file.filename)
            file.save(filepath)

            tipo = "video" if file.filename.lower().endswith((".mp4", ".mov", ".avi")) else "imagen"
            usuario = session.get("usuario")

            cursor.execute(
                "INSERT INTO multimedia (tipo, nombre, ruta, usuario) VALUES (%s, %s, %s, %s)",
                (tipo, file.filename, f"uploads/{file.filename}", usuario)
            )
            mysql.connection.commit()

            flash("Archivo subido correctamente", "success")
            return redirect(url_for("upload"))

        cursor.execute("SELECT id, tipo, nombre, ruta, usuario, fecha FROM multimedia ORDER BY id DESC")
        multimedia = cursor.fetchall()
    finally:
        cursor.close()

    return render_template("upload.html", multimedia=multimedia, user_authenticated=user_authenticated())

# ----------------------
# Comentarios
# ----------------------
@app.route("/comentarios", methods=["GET", "POST"])
@login_required
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

        cursor.execute("SELECT id, username, comentario FROM comentarios ORDER BY fecha DESC")
        comentarios_db = cursor.fetchall()
    finally:
        cursor.close()

    return render_template("comentarios.html", comentarios=comentarios_db, user_authenticated=user_authenticated())


# ==================================================================
# RUTAS DE LA TIENDA Y PANEL DE ADMIN (CON SUBIDA DE IMAGEN)
# ==================================================================

# ----------------------
# TIENDA - Catálogo de Productos
# ----------------------
@app.route('/tienda')
def tienda():
    cursor = mysql.connection.cursor(DictCursor)
    try:
        cursor.execute("SELECT * FROM productos WHERE stock > 0")
        productos = cursor.fetchall()
    finally:
        cursor.close()
    return render_template('tienda.html', productos=productos, user_authenticated=user_authenticated())

# ----------------------
# TIENDA - Panel de Admin (Agregar)
# ----------------------
@app.route('/admin/productos', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_productos():
    cursor = mysql.connection.cursor(DictCursor)
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = request.form['precio']
        stock = request.form['stock']
        
        imagen_url_db = None  # Valor por defecto si no se sube imagen

        if 'imagen_file' in request.files:
            file = request.files['imagen_file']
            if file.filename != '':
                try:
                    filename = secure_filename(file.filename)
                    save_path = os.path.join(app.config['PRODUCT_UPLOAD_FOLDER'], filename)
                    file.save(save_path)
                    # Ruta relativa a 'static/' para guardar en BD
                    imagen_url_db = f'uploads/productos/{filename}'
                    flash('Imagen subida correctamente', 'success')
                except Exception as e:
                    flash(f'Error al subir la imagen: {str(e)}', 'error')

        try:
            cursor.execute(
                "INSERT INTO productos (nombre, descripcion, precio, stock, imagen_url) VALUES (%s, %s, %s, %s, %s)",
                (nombre, descripcion, precio, stock, imagen_url_db)
            )
            mysql.connection.commit()
            flash('Producto agregado correctamente', 'success')
        except Exception as e:
            flash(f'Error al agregar producto: {str(e)}', 'error')
        
        return redirect(url_for('admin_productos'))

    # GET: Mostrar formulario y lista de productos
    try:
        cursor.execute("SELECT * FROM productos ORDER BY id DESC")
        productos = cursor.fetchall()
    finally:
        cursor.close()
        
    return render_template('admin_productos.html', productos=productos, user_authenticated=user_authenticated())

# ----------------------
# TIENDA - Modificar Producto
# ----------------------
@app.route('/admin/productos/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def modificar_producto(id):
    cursor = mysql.connection.cursor(DictCursor)
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = request.form['precio']
        stock = request.form['stock']
        # Obtener la ruta de la imagen actual desde el campo oculto
        imagen_url_db = request.form.get('imagen_actual') 

        # Lógica para subir una NUEVA imagen (si se provee una)
        if 'imagen_file' in request.files:
            file = request.files['imagen_file']
            if file.filename != '':
                try:
                    filename = secure_filename(file.filename)
                    save_path = os.path.join(app.config['PRODUCT_UPLOAD_FOLDER'], filename)
                    file.save(save_path)
                    imagen_url_db = f'uploads/productos/{filename}' # Actualizar la ruta
                    flash('Imagen actualizada correctamente', 'success')
                except Exception as e:
                    flash(f'Error al subir nueva imagen: {str(e)}', 'error')

        try:
            cursor.execute("""
                UPDATE productos 
                SET nombre=%s, descripcion=%s, precio=%s, stock=%s, imagen_url=%s 
                WHERE id=%s
            """, (nombre, descripcion, precio, stock, imagen_url_db, id))
            mysql.connection.commit()
            flash('Producto actualizado correctamente', 'success')
        except Exception as e:
            flash(f'Error al actualizar producto: {str(e)}', 'error')
        finally:
            cursor.close()

        return redirect(url_for('admin_productos'))

    # GET: Mostrar formulario con datos del producto
    try:
        cursor.execute("SELECT * FROM productos WHERE id = %s", (id,))
        producto = cursor.fetchone()
    finally:
        cursor.close()

    if not producto:
        flash('Producto no encontrado', 'error')
        return redirect(url_for('admin_productos'))
        
    return render_template('modificar_producto.html', producto=producto, user_authenticated=user_authenticated())

# ----------------------
# TIENDA - Eliminar Producto
# ----------------------
@app.route('/admin/productos/eliminar/<int:id>', methods=['POST'])
@login_required
@role_required('admin')
def eliminar_producto(id):
    # (Opcional: lógica para eliminar el archivo de imagen del servidor)
    cursor = mysql.connection.cursor()
    try:
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
# CARRITO - Agregar Producto
# ----------------------
@app.route('/carrito/agregar/<int:id>', methods=['POST'])
@login_required
def agregar_al_carrito(id):
    if 'carrito' not in session:
        session['carrito'] = {}

    carrito = session['carrito']
    producto_id = str(id)
    
    try:
        cantidad = int(request.form.get('cantidad', 1))
        if cantidad < 1:
            cantidad = 1
    except ValueError:
        cantidad = 1

    if producto_id in carrito:
        carrito[producto_id] += cantidad
    else:
        carrito[producto_id] = cantidad
    
    session.modified = True
    flash(f'Producto agregado al carrito (Cantidad: {cantidad})', 'success')
    
    return redirect(url_for('tienda'))

# ----------------------
# CARRITO - Ver Carrito
# ----------------------
@app.route('/carrito')
@login_required
def ver_carrito():
    if 'carrito' not in session or not session['carrito']:
        return render_template('carrito.html', items_en_carrito=[], total=0, user_authenticated=user_authenticated())

    carrito = session['carrito']
    ids_productos = list(carrito.keys())
    
    if not ids_productos:
         return render_template('carrito.html', items_en_carrito=[], total=0, user_authenticated=user_authenticated())

    placeholders = ', '.join(['%s'] * len(ids_productos))
    
    cursor = mysql.connection.cursor(DictCursor)
    try:
        cursor.execute(f"SELECT * FROM productos WHERE id IN ({placeholders})", tuple(ids_productos))
        productos = cursor.fetchall()
    finally:
        cursor.close()

    items_en_carrito = []
    total = 0
    
    for producto in productos:
        producto_id = str(producto['id'])
        cantidad = carrito.get(producto_id, 0)
        
        if cantidad > 0:
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

    return render_template('carrito.html', items_en_carrito=items_en_carrito, total=total, user_authenticated=user_authenticated())

# ----------------------
# CARRITO - Eliminar Producto
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
# Borradores y Gestión de Usuarios
# ==================================================================

@app.route("/borrar_imagen/<int:id>", methods=["POST"])
@login_required
@role_required("admin")
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

@app.route("/borrar_comentario/<int:id>", methods=["POST"])
@login_required
@role_required("admin")
def borrar_comentario(id):
    cursor = mysql.connection.cursor(DictCursor)
    try:
        cursor.execute("DELETE FROM comentarios WHERE id = %s", (id,))
        mysql.connection.commit()
        flash("Comentario eliminado", "success")
    finally:
        cursor.close()

    return redirect(url_for("comentarios"))

@app.route("/usuarios")
@login_required
@role_required("admin")
def usuarios():
    cursor = mysql.connection.cursor(DictCursor)
    try:
        cursor.execute("SELECT id, nombre, apellidos, username, email, rol FROM regis")
        usuarios = cursor.fetchall()
    finally:
        cursor.close()

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

    return render_template("modificar_usuario.html", usuario=usuario, user_authenticated=user_authenticated())