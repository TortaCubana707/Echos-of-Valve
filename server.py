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


