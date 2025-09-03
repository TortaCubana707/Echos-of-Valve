from flask import Flask, render_template, request, redirect, url_for, flash, session
import os
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "clave_secreta"  # necesario para sesiones y flash

# ----------------------
# Conexión a la base de datos
# ----------------------
def get_db_connection():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",          # usuario de XAMPP
        password="",          # contraseña de MySQL (si tiene, cámbiala aquí)
        database="evalve"    # ⚠️ usa aquí el nombre de tu BD (no la tabla)
    )
    return conn

# ----------------------
# Funciones auxiliares
# ----------------------
def user_authenticated():
    """Verifica si el usuario está logueado"""
    return session.get("logged_in", False)

# ----------------------
# Rutas de autenticación
# ----------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM regis WHERE username = %s", (usuario,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["logged_in"] = True
            session["usuario"] = usuario
            session["rol"] = user["rol"]  # <-- guardamos el rol
            flash("Has iniciado sesión correctamente", "success")
            return redirect(url_for("index"))
        else:
            flash("Usuario o contraseña incorrectos", "error")
            return redirect(url_for("login"))

    return render_template("login.html", user_authenticated=user_authenticated(), show_aside=False)



@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        usrname = request.form["usrname"]
        usrln = request.form["usrln"]
        usrn = request.form["usrn"]
        usrmail = request.form["usrmail"]
        usrpass = request.form["usrpass"]

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO regis (nombre, apellidos, username, email, password) VALUES (%s, %s, %s, %s, %s)",
                (usrname, usrln, usrn, usrmail, generate_password_hash(usrpass))
            )
            conn.commit()
            flash("Registro exitoso", "success")
            return redirect(url_for("login"))
        except mysql.connector.IntegrityError:
            flash("El usuario o correo ya existe", "error")
            return redirect(url_for("register"))
        finally:
            cursor.close()
            conn.close()

    return render_template("forms/register.html", user_authenticated=user_authenticated(), show_aside=False)


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
    return render_template(
        'index.html',
        user_authenticated=user_authenticated(),
        show_aside=True,
        fondo="Fondo.gif"
    )

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
    juego = {
        "nombre": nombre,
        "titulo": nombre.capitalize(),
        "descripcion": "Aquí puedes poner una descripción detallada del juego, su historia, desarrollo y curiosidades."
    }

    return render_template(
        "juego.html",
        juego=juego,
        fondo=fondo,
        user_authenticated=user_authenticated(),
        show_aside=True
    )

# ----------------------
# Subida de imágenes
# ----------------------
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if not user_authenticated():
        flash("Debes iniciar sesión para subir archivos", "error")
        return redirect(url_for("login"))

    conn = get_db_connection()
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
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)

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

    # Traer todos los archivos
    cursor.execute("SELECT * FROM multimedia ORDER BY fecha DESC")
    multimedia = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "upload.html",
        multimedia=multimedia,
        user_authenticated=user_authenticated(),
        show_aside=True
    )

@app.route("/comentarios", methods=["GET", "POST"])
def comentarios():
    if not user_authenticated():
        flash("Debes iniciar sesión para comentar", "error")
        return redirect(url_for("login"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == "POST":
        texto = request.form["comentario"]
        usuario = session.get("usuario")  # usa el usuario logueado

        cursor.execute(
            "INSERT INTO comentarios (username, comentario) VALUES (%s, %s)",
            (usuario, texto)
        )
        conn.commit()
        flash("Comentario publicado", "success")

    # Trae todos los comentarios ordenados por fecha, incluyendo el id
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


