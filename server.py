from flask import Flask, render_template, redirect, url_for, flash, session, request
import os
# Asumiendo que config.py y forms.py existen en el mismo directorio
from config import AppConfig
from forms import LoginForm, RegisterForm
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mysqldb import MySQL
from MySQLdb.cursors import DictCursor
from functools import wraps  # ✅ Import necesario para los decoradores

app = Flask(__name__)
app.config.from_object(AppConfig)

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
    # Redirigir si ya está logueado
    if user_authenticated():
        return redirect(url_for('index'))
        
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
            flash("Has iniciado sesión correctamente", "success")
            return redirect(url_for("index"))
        else:
            flash("Usuario o contraseña incorrectos", "error")

    # No es necesario 'show_aside=False' porque ya quitamos el aside de base.html
    return render_template("login.html", form=form, user_authenticated=user_authenticated())

# ----------------------
# Registro con WTForms
# ----------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    # Redirigir si ya está logueado
    if user_authenticated():
        return redirect(url_for('index'))

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
    flash("Has cerrado sesión", "success") # Cambiado a 'success' para que se vea verde
    return redirect(url_for('index'))

# ----------------------
# Página principal
# ----------------------
@app.route('/')
def index():
    return render_template('index.html', user_authenticated=user_authenticated(), fondo="Fondo.gif")

# ----------------------
# Página de juegos (Página individual)
# ----------------------
@app.route("/juego/<nombre>")
def juego(nombre):
    fondos = {
        "half-life": "FondoHL.jpg",
        "cs": "FondoCS.jpg",
        "portal": "FondoPortal.jpg",
        "tf2": "FondoTF2.jpg",
        "l4d": "FondoL4D.jpg",
        "l4d2": "FondoL4D2.jpg",
        "dota2": "FondoDota2.jpg",
        "alyx": "FondoAlyx.jpg"
    }
    fondo = fondos.get(nombre, "Fondo.gif")
    
    # Lógica para juegos que requieren autenticación
    juegos_privados = ["l4d", "l4d2", "dota2", "alyx"]
    if nombre in juegos_privados and not user_authenticated():
        flash("Debes iniciar sesión para ver este contenido.", "error")
        return redirect(url_for('login'))

    juego = {"nombre": nombre, "titulo": nombre.replace('-', ' ').capitalize(), "descripcion": "Aquí puedes poner una descripción detallada del juego."}
    return render_template("juego.html", juego=juego, fondo=fondo, user_authenticated=user_authenticated())

# ----------------------
# NUEVA RUTA: Página de lista de Juegos
# ----------------------
@app.route("/juegos")
def juegos():
    # Definimos todos los juegos con sus datos
    juegos_lista = [
        {'nombre': 'half-life', 'titulo': 'Half-Life', 'imagen': 'img/juego-hl.jpg', 'auth_required': False},
        {'nombre': 'cs', 'titulo': 'Counter-Strike', 'imagen': 'img/juego-cs.jpg', 'auth_required': False},
        {'nombre': 'portal', 'titulo': 'Portal', 'imagen': 'img/juego-portal.jpg', 'auth_required': False},
        {'nombre': 'tf2', 'titulo': 'Team Fortress 2', 'imagen': 'img/juego-tf2.jpg', 'auth_required': False},
        {'nombre': 'l4d', 'titulo': 'Left 4 Dead', 'imagen': 'img/juego-l4d.jpg', 'auth_required': True},
        {'nombre': 'l4d2', 'titulo': 'Left 4 Dead 2', 'imagen': 'img/juego-l4d2.jpg', 'auth_required': True},
        {'nombre': 'dota2', 'titulo': 'Dota 2', 'imagen': 'img/juego-dota2.jpg', 'auth_required': True},
        {'nombre': 'alyx', 'titulo': 'Half-Life: Alyx', 'imagen': 'img/juego-alyx.jpg', 'auth_required': True}
    ]

    # Filtramos la lista dependiendo de si el usuario está autenticado
    if user_authenticated():
        juegos_a_mostrar = juegos_lista
    else:
        juegos_a_mostrar = [juego for juego in juegos_lista if not juego['auth_required']]
        # Añadimos un indicador a los juegos bloqueados
        for juego in juegos_lista:
            if juego['auth_required']:
                juego['bloqueado'] = True
                juegos_a_mostrar.append(juego)


    return render_template("juegos.html", juegos=juegos_a_mostrar, user_authenticated=user_authenticated())

# ----------------------
# NUEVA RUTA: Tienda
# ----------------------
@app.route("/tienda")
def tienda():
    return render_template("tienda.html", user_authenticated=user_authenticated())

# ----------------------
# Subida de archivos
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

        cursor.execute("SELECT id, username, comentario FROM comentarios ORDER BY fecha DESC")
        comentarios_db = cursor.fetchall()
    finally:
        cursor.close()

    return render_template("comentarios.html", comentarios=comentarios_db, user_authenticated=user_authenticated())

# ----------------------
# Borrar imagen (solo admin)
# ----------------------
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

# ----------------------
# Manejador de errores (ejemplo 404)
# ----------------------
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', user_authenticated=user_authenticated()), 404


