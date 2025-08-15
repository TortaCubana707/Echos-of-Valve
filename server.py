from flask import Flask, render_template, redirect, url_for

app = Flask(__name__)

# Ruta de inicio
@app.route("/")  # ruta en el navegador
def index():
    # Pasamos show_aside=True para que se muestre el menú lateral
    return render_template("index.html", show_aside=True)

# Ruta de login
@app.route('/login')
def login():
    # No mostrar el menú lateral en login
    return render_template("login.html", show_aside=False)

# Ruta de registro
@app.route('/register')
def registro():
    # No mostrar el menú lateral en registro
    return render_template("forms/register.html", show_aside=False)

if __name__ == "__main__":
    app.run(debug=True)
