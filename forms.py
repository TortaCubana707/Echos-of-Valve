from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length

# ----------------------
# Formulario de Login
# ----------------------
class LoginForm(FlaskForm):
    usuario = StringField(
        "Usuario",
        validators=[DataRequired(message="El usuario es obligatorio")]
    )
    password = PasswordField(
        "Contraseña",
        validators=[DataRequired(message="La contraseña es obligatoria")]
    )
    submit = SubmitField("Iniciar sesión")

# ----------------------
# Formulario de Registro
# ----------------------
class RegisterForm(FlaskForm):
    usrname = StringField(
        "Nombre",
        validators=[DataRequired(message="El nombre es obligatorio"), Length(min=2, max=50)]
    )
    usrln = StringField(
        "Apellidos",
        validators=[DataRequired(message="Los apellidos son obligatorios"), Length(min=2, max=50)]
    )
    usrn = StringField(
        "Nombre de usuario",
        validators=[DataRequired(message="El nombre de usuario es obligatorio"), Length(min=3, max=20)]
    )
    usrmail = StringField(
        "Correo electrónico",
        validators=[DataRequired(message="El correo es obligatorio"), Email(message="Correo inválido")]
    )
    usrpass = PasswordField(
        "Contraseña",
        validators=[DataRequired(message="La contraseña es obligatoria"), Length(min=6, message="Mínimo 6 caracteres")]
    )
    confirm_pass = PasswordField(
        "Confirmar contraseña",
        validators=[
            DataRequired(message="Debes confirmar tu contraseña"),
            EqualTo("usrpass", message="Las contraseñas no coinciden")
        ]
    )
    submit = SubmitField("Registrarse")
