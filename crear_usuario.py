import mysql.connector
from werkzeug.security import generate_password_hash

# Conexión a la base de datos
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="evalve"
)
cursor = conn.cursor()

# Datos del usuario de prueba
usuario = "Mamor123"
password = generate_password_hash("1234")

# Inserta el usuario
try:
    cursor.execute("""
        INSERT INTO regis (nombre, apellidos, username, email, password)
        VALUES (%s, %s, %s, %s, %s)
    """, ("Celia", "Hernandez", usuario, "Mujer@test.com", password))
    conn.commit()
    print("Usuario de prueba creado correctamente.")
except mysql.connector.IntegrityError:
    print("El usuario ya existe.")
finally:
    cursor.close()
    conn.close()
