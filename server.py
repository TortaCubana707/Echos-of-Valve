from flask import Flask, render_template, redirect, url_for, flash, session, request
import os
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from forms import LoginForm, RegisterForm  # 👈 Importamos los formularios

app = Flask(__name__)
app.secret_key = "clave_secreta"

# ----------------------
# Conexión a la base de datos
# ----------------------
def get_db_connection():
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="",
            database="evalve"
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Error al conectar a MySQL: {err}")
        return None

# ----------------------
# Función auxiliar
# ----------------------
def user_authenticated():
    return session.get("logged_in", False)

# ----------------------
# Login con WTForms
# ----------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        usuario = form.usuario.data.strip()
        password = form.password.data

        conn = get_db_connection()
        if conn is None:
            flash("No se pudo conectar a la base de datos", "error")
            return redirect(url_for("login"))

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM regis WHERE username = %s", (usuario,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["logged_in"] = True
            session["usuario"] = usuario
            session["rol"] = user.get("rol", "usuario")
            flash("Has iniciado sesión correctamente", "success")
            return redirect(url_for("index"))
        else:
            flash("Usuario o contraseña incorrectos", "error")

    return render_template("login.html", form=form, user_authenticated=user_authenticated(), show_aside=False)

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

        conn = get_db_connection()
        if conn is None:
            flash("No se pudo conectar a la base de datos", "error")
            return redirect(url_for("register"))

        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO regis (nombre, apellidos, username, email, password, rol) VALUES (%s, %s, %s, %s, %s, %s)",
                (usrname, usrln, usrn, usrmail, generate_password_hash(usrpass), "usuario")
            )
            conn.commit()
            flash("Registro exitoso", "success")
            return redirect(url_for("login"))
        except mysql.connector.IntegrityError:
            flash("El usuario o correo ya existe", "error")
        finally:
            cursor.close()
            conn.close()

    return render_template("forms/register.html", form=form, user_authenticated=user_authenticated(), show_aside=False)

# ----------------------
# Logout
# ----------------------
@app.route('/logout')
def logout():
    session.pop("logged_in", None)
    session.pop("usuario", None)
    flash("Has cerrado sesión")
    return redirect(url_for('index'))

# ----------------------
# Página principal
# ----------------------
@app.route('/')
def index():
    return render_template('index.html', user_authenticated=user_authenticated(), show_aside=True, fondo="Fondo.gif")

# ----------------------
# Página de juegos
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
    juego = {"nombre": nombre, "titulo": nombre.capitalize(), "descripcion": "Aquí puedes poner una descripción detallada del juego."}
    return render_template("juego.html", juego=juego, fondo=fondo, user_authenticated=user_authenticated(), show_aside=True)

# ----------------------
# Subida de imágenes
# ----------------------
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if not user_authenticated():
        flash("Debes iniciar sesión para subir archivos", "error")
        return redirect(url_for("login"))

    conn = get_db_connection()
    if conn is None:
        flash("No se pudo conectar a la base de datos", "error")
        return redirect(url_for("index"))

    cursor = conn.cursor(dictionary=True)

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
        conn.commit()

        flash("Archivo subido correctamente", "success")
        return redirect(url_for("upload"))

    cursor.execute("SELECT * FROM multimedia ORDER BY fecha DESC")
    multimedia = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("upload.html", multimedia=multimedia, user_authenticated=user_authenticated(), show_aside=True)

# ----------------------
# Comentarios
# ----------------------
@app.route("/comentarios", methods=["GET", "POST"])
def comentarios():
    if not user_authenticated():
        flash("Debes iniciar sesión para comentar", "error")
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        texto = request.form["comentario"]
        usuario = session.get("usuario")
        cursor.execute("INSERT INTO comentarios (username, comentario) VALUES (%s, %s)", (usuario, texto))
        conn.commit()
        flash("Comentario publicado", "success")

    cursor.execute("SELECT id, username, comentario FROM comentarios ORDER BY fecha DESC")
    comentarios_db = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template("comentarios.html", comentarios=comentarios_db, user_authenticated=user_authenticated(), show_aside=True)

@app.route("/borrar_comentario/<int:id>", methods=["POST"])
def borrar_comentario(id):
    if session.get("rol") != "admin":
        flash("No tienes permiso para borrar comentarios", "error")
        return redirect(url_for("comentarios"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM comentarios WHERE id = %s", (id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash("Comentario eliminado", "success")
    return redirect(url_for("comentarios"))

