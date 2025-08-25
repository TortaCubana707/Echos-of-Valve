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
        # Lógica simple de verificación (puedes reemplazar con base de datos)
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
    show_aside = True
    return render_template('index.html', user_authenticated=user_authenticated(), show_aside=show_aside)

# ----------------------
# Página de juegos
# ----------------------
@app.route('/juego/<nombre>')
def juego(nombre):
    juegos = {
        "half-life": {"titulo": "Half-Life", "descripcion": "Lanzado en 1998, revolucionó los FPS con su narrativa inmersiva..."},
        "cs": {"titulo": "Counter-Strike", "descripcion": "De mod de Half-Life a fenómeno global, definió los shooters tácticos..."},
        "portal": {"titulo": "Portal", "descripcion": "Introdujo mecánicas de puzzles únicas y humor de GLaDOS..."},
        "tf2": {"titulo": "Team Fortress 2", "descripcion": "Shooter multijugador por clases con estilo único..."},
        "l4d": {"titulo": "Left 4 Dead", "descripcion": "Shooter cooperativo con hordas de zombis y Director IA..."},
        "l4d2": {"titulo": "Left 4 Dead 2", "descripcion": "Secuela con más campañas, armas y modos de juego cooperativos..."},
        "dota2": {"titulo": "Dota 2", "descripcion": "MOBA influyente con héroes variados y actualizaciones constantes..."},
        "alyx": {"titulo": "Half-Life: Alyx", "descripcion": "Exclusivo para VR, interacción física y narrativa inmersiva..."}
    }
    juego_info = juegos.get(nombre, {"titulo": "Juego no encontrado", "descripcion": "No hay información disponible."})
    juego_info['nombre'] = nombre
    return render_template("juego.html", show_aside=True, user_authenticated=user_authenticated(), juego=juego_info)

