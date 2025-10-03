from flask import Flask, render_template, request, redirect, url_for, flash, session
import os

app = Flask(__name__)
app.secret_key = "clave_secreta"  # necesario para sesiones y flash

# ----------------------
# Funciones auxiliares
# ----------------------
def user_authenticated():
    """Verifica si el usuario está logueado"""
    return session.get("logged_in", False)

# ----------------------
# Rutas de autenticación
# ----------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']
        if usuario == "admin" and password == "1234":
            session["logged_in"] = True
            flash("Has iniciado sesión correctamente")
            return redirect(url_for('index'))
        else:
            flash("Usuario o contraseña incorrectos")
            return redirect(url_for('login'))
    return render_template("login.html", user_authenticated=user_authenticated(), show_aside=False)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # lógica de registro
        flash('Registro exitoso')
        return redirect(url_for('index'))
    return render_template('forms/register.html', user_authenticated=user_authenticated(), show_aside=False)


@app.route('/logout')
def logout():
    session.pop("logged_in", None)
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
    if request.method == 'POST':
        if "imagen" not in request.files:
            flash("No se seleccionó archivo")
            return redirect(request.url)

        file = request.files["imagen"]

        if file.filename == "":
            flash("Nombre de archivo vacío")
            return redirect(request.url)

        if file:
            upload_folder = os.path.join(app.root_path, "static/uploads")
            if not os.path.exists(upload_folder):
                os.makedirs(upload_folder)
            filepath = os.path.join(upload_folder, file.filename)
            file.save(filepath)
            flash("Imagen subida exitosamente")
            return redirect(url_for("upload", filename=file.filename))

    filename = request.args.get("filename")
    return render_template(
        "upload.html",
        user_authenticated=user_authenticated(),
        show_aside=True,
        filename=filename
    )


<<<<<<< HEAD
=======
            flash("Archivo subido correctamente", "success")
            return redirect(url_for("upload"))

        # Traer todas las imágenes/videos para mostrarlas, ordenando por ID descendente
        cursor.execute("SELECT id, tipo, nombre, ruta, usuario, fecha FROM multimedia ORDER BY id DESC")
        multimedia = cursor.fetchall()
    finally:
        cursor.close()

    return render_template("upload.html", multimedia=multimedia, user_authenticated=user_authenticated(), show_aside=True)

# ----------------------
# Comentarios
# ----------------------
@app.route("/comentarios", methods=["GET", "POST"])
def comentarios():
    if not user_authenticated():
        flash("Debes iniciar sesión para comentar", "error")
        return redirect(url_for("login"))

    cursor = mysql.connection.cursor(DictCursor)
    try:
        if request.method == "POST":
            texto = request.form["comentario"]
            usuario = session.get("usuario")
            cursor.execute("INSERT INTO comentarios (username, comentario) VALUES (%s, %s)", (usuario, texto))
            mysql.connection.commit()
            flash("Comentario publicado", "success")

        cursor.execute("SELECT id, username, comentario FROM comentarios ORDER BY fecha DESC")
        comentarios_db = cursor.fetchall()
    finally:
        cursor.close()

    return render_template("comentarios.html", comentarios=comentarios_db, user_authenticated=user_authenticated(), show_aside=True)

# ----------------------
# Borrar comentario
# ----------------------
@app.route("/borrar_imagen/<int:id>", methods=["POST"])
def borrar_imagen(id):
    if session.get("rol") != "admin":
        flash("No tienes permiso para borrar esta imagen", "error")
        return redirect(url_for("upload"))

    cursor = mysql.connection.cursor(DictCursor)
    try:
        # Obtener ruta del archivo para borrarlo
        cursor.execute("SELECT ruta FROM multimedia WHERE id = %s", (id,))
        img = cursor.fetchone()
        if img:
            filepath = os.path.join(app.root_path, "static", img["ruta"])
            if os.path.exists(filepath):
                os.remove(filepath)

            # Borrar registro de la base de datos
            cursor.execute("DELETE FROM multimedia WHERE id = %s", (id,))
            mysql.connection.commit()
            flash("Imagen eliminada", "success")
    finally:
        cursor.close()

    return redirect(url_for("upload"))

@app.route("/borrar_comentario/<int:id>", methods=["POST"])
def borrar_comentario(id):
    if session.get("rol") != "admin":
        flash("No tienes permiso para borrar este comentario", "error")
        return redirect(url_for("comentarios"))

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
def usuarios():
    if session.get("rol") != "admin":
        flash("No tienes permiso para acceder a esta página", "error")
        return redirect(url_for("index"))

    cursor = mysql.connection.cursor(DictCursor)
    try:
        cursor.execute("SELECT id, nombre, apellidos, username, email, rol FROM regis")
        usuarios = cursor.fetchall()
    finally:
        cursor.close()

    return render_template("usuarios.html", usuarios=usuarios, user_authenticated=user_authenticated(), show_aside=True)

@app.route("/eliminar_usuario/<int:id>", methods=["POST"])
def eliminar_usuario(id):
    if session.get("rol") != "admin":
        flash("No tienes permiso para eliminar usuarios", "error")
        return redirect(url_for("usuarios"))

    cursor = mysql.connection.cursor()
    try:
        cursor.execute("DELETE FROM regis WHERE id = %s", (id,))
        mysql.connection.commit()
        flash("Usuario eliminado correctamente", "success")
    finally:
        cursor.close()

    return redirect(url_for("usuarios"))

@app.route("/modificar_usuario/<int:id>", methods=["GET", "POST"])
def modificar_usuario(id):
    if session.get("rol") != "admin":
        flash("No tienes permiso para modificar usuarios", "error")
        return redirect(url_for("usuarios"))

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

    return render_template("modificar_usuario.html", usuario=usuario, user_authenticated=user_authenticated(), show_aside=True)
>>>>>>> 326759dc7b27aa119b6d51f9859935d8bf2f450f
