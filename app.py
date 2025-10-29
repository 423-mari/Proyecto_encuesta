from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from conexion import get_connection

# ---------- Configuración Flask ----------
app = Flask(__name__)
app.secret_key = "supersecretkey"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# ---------- Modelo de usuario ----------
class User(UserMixin):
    def __init__(self, id, nombre, correo, rol):
        self.id = id
        self.nombre = nombre
        self.correo = correo
        self.rol = rol

@login_manager.user_loader
def load_user(user_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM usuarios WHERE id = ?", (user_id,))
    user = cur.fetchone()
    conn.close()
    if user:
        return User(user[0], user[1], user[2], user[4])
    return None

# ---------- Rutas de autenticación ----------
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        correo = request.form["correo"]
        password = request.form["password"]
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM usuarios WHERE correo = ?", (correo,))
        user = cur.fetchone()
        conn.close()
        if user and check_password_hash(user[3], password):  # password_hash
            u = User(user[0], user[1], user[2], user[4])
            login_user(u)
            return redirect(url_for("panel"))
        flash("Correo o contraseña incorrectos", "danger")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# ---------- Panel principal ----------
@app.route("/")
@login_required
def panel():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM encuestas")
    encuestas = cur.fetchall()
    conn.close()
    return render_template("index.html", encuestas=encuestas, usuario=current_user)

# ---------- Registrar usuarios (solo admin) ----------
@app.route("/register", methods=["GET","POST"])
@login_required
def register():
    if current_user.rol != "administrador":
        flash("No tienes permisos", "danger")
        return redirect(url_for("panel"))
    if request.method == "POST":
        nombre = request.form["nombre"]
        correo = request.form["correo"]
        rol = request.form["rol"]
        password = generate_password_hash(request.form["password"])
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO usuarios (nombre, correo, rol, password_hash) VALUES (?, ?, ?, ?)",
                    (nombre, correo, rol, password))
        conn.commit()
        conn.close()
        flash("Usuario registrado exitosamente", "Dark")
        return redirect(url_for("register"))
    return render_template("register.html")

# ---------- Crear nueva encuesta ----------
@app.route("/encuestas/nueva", methods=["GET","POST"])
@login_required
def nueva_encuesta():
    if current_user.rol != "administrador":
        flash("No tienes permisos", "danger")
        return redirect(url_for("panel"))
    if request.method == "POST":
        titulo = request.form["titulo"]
        descripcion = request.form["descripcion"]
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO encuestas (titulo, descripcion) VALUES (?, ?)", (titulo, descripcion))
        conn.commit()
        conn.close()
        flash("Encuesta creada", "success")
        return redirect(url_for("panel"))
    return render_template("nueva_encuesta.html")

# ---------- Preguntas ----------
@app.route("/encuestas/<int:id_encuesta>/preguntas", methods=["GET","POST"])
@login_required
def preguntas(id_encuesta):
    if current_user.rol != "administrador":
        flash("No tienes permisos", "danger")
        return redirect(url_for("panel"))
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM encuestas WHERE id = ?", (id_encuesta,))
    encuesta = cur.fetchone()
    if request.method == "POST":
        texto = request.form["texto_pregunta"]
        tipo = request.form["tipo"]
        cur.execute("INSERT INTO preguntas (id_encuesta, texto_pregunta, tipo) VALUES (?, ?, ?)",
                    (id_encuesta, texto, tipo))
        conn.commit()
    cur.execute("SELECT * FROM preguntas WHERE id_encuesta = ?", (id_encuesta,))
    preguntas = cur.fetchall()
    conn.close()
    return render_template("preguntas.html", encuesta=encuesta, preguntas=preguntas)

# ---------- Editar pregunta ----------
@app.route("/pregunta/<int:id_pregunta>/editar", methods=["GET","POST"])
@login_required
def editar_pregunta(id_pregunta):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM preguntas WHERE id = ?", (id_pregunta,))
    pregunta = cur.fetchone()

    if not pregunta:
        flash("Pregunta no encontrada", "danger")
        return redirect(url_for("panel"))

    # Obtener la encuesta a la que pertenece la pregunta
    id_encuesta = pregunta[1]  # suponiendo que la columna 1 es id_encuesta
    cur.execute("SELECT * FROM encuestas WHERE id = ?", (id_encuesta,))
    encuesta = cur.fetchone()

    # Obtener todas las preguntas de esa encuesta
    cur.execute("SELECT * FROM preguntas WHERE id_encuesta = ?", (id_encuesta,))
    preguntas = cur.fetchall()

    if request.method == "POST":
        nuevo_texto = request.form["texto_pregunta"]
        cur.execute("UPDATE preguntas SET texto_pregunta = ? WHERE id = ?", (nuevo_texto, id_pregunta))
        conn.commit()
        conn.close()
        flash("Pregunta actualizada correctamente", "success")
        return redirect(url_for("preguntas", id_encuesta=id_encuesta))

    conn.close()
    return render_template("preguntas.html", encuesta=encuesta, preguntas=preguntas, editar=pregunta)

# ---------- Eliminar pregunta  admin----------
@app.route("/pregunta/<int:id_pregunta>/eliminar", methods=["POST"])
@login_required
def eliminar_pregunta(id_pregunta):
    if current_user.rol != "administrador":
        flash("No tienes permisos para eliminar preguntas", "danger")
        return redirect(url_for("panel"))

    conn = get_connection()
    cur = conn.cursor()
    # Buscamos el id_encuesta antes de eliminar
    cur.execute("SELECT id_encuesta FROM preguntas WHERE id=?", (id_pregunta,))
    result = cur.fetchone()
    if result:
        id_encuesta = result[0]
        cur.execute("DELETE FROM preguntas WHERE id=?", (id_pregunta,))
        conn.commit()
        flash("Pregunta eliminada correctamente", "warning")
    else:
        flash("La pregunta no existe", "danger")

    conn.close()
    return redirect(url_for("preguntas", id_encuesta=id_encuesta))

# ---------- Responder encuesta ----------
@app.route("/encuestas/<int:id_encuesta>/responder", methods=["GET","POST"])
@login_required
def responder(id_encuesta):
    conn = get_connection()
    cur = conn.cursor()
    # Obtener encuesta y preguntas con respuestas previas
    cur.execute('SELECT id, titulo FROM encuestas WHERE id = ?', (id_encuesta,))
    encuesta = cur.fetchone()
    cur.execute('''SELECT p.id, p.texto_pregunta, p.tipo, r.respuesta_texto, r.valor
                   FROM preguntas p
                   LEFT JOIN respuestas r ON p.id = r.id_pregunta AND r.id_usuario=?
                   WHERE p.id_encuesta = ?''', (current_user.id, id_encuesta))
    preguntas = cur.fetchall()

    if request.method == 'POST':
        for p in preguntas:
            pid = p[0]
            tipo = p[2]
            if tipo == 'valor':
                val = request.form.get(f'valor_{pid}')
                if val:
                    cur.execute('INSERT OR REPLACE INTO respuestas (id_pregunta, id_usuario, valor) VALUES (?, ?, ?)',
                                (pid, current_user.id, int(val)))
            else:
                txt = request.form.get(f'txt_{pid}')
                cur.execute('INSERT OR REPLACE INTO respuestas (id_pregunta, id_usuario, respuesta_texto) VALUES (?, ?, ?)',
                            (pid, current_user.id, txt))
        conn.commit()
        flash('Respuestas guardadas correctamente.', 'success')
        return redirect(url_for('panel'))

    conn.close()
    return render_template('responder.html', encuesta=encuesta, preguntas=preguntas, usuario=current_user)

# ---------- Eliminar respuestas ----------
@app.route("/encuestas/<int:id_encuesta>/eliminar_respuestas")
@login_required
def eliminar_respuestas(id_encuesta):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM respuestas WHERE id_usuario=? AND id_pregunta IN (SELECT id FROM preguntas WHERE id_encuesta=?)",
                (current_user.id, id_encuesta))
    conn.commit()
    conn.close()
    flash("Respuestas eliminadas", "warning")
    return redirect(url_for("responder", id_encuesta=id_encuesta))

# ---------- Ver resultados ----------
@app.route("/encuestas/<int:id_encuesta>/resultados")
@login_required
def resultados(id_encuesta):
    if current_user.rol != "administrador":
        flash("No tienes permisos", "danger")
        return redirect(url_for("panel"))
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM encuestas WHERE id=?", (id_encuesta,))
    encuesta = cur.fetchone()
    cur.execute('''SELECT p.texto_pregunta, p.tipo, r.valor, r.respuesta_texto, u.nombre
                   FROM preguntas p
                   LEFT JOIN respuestas r ON p.id = r.id_pregunta
                   LEFT JOIN usuarios u ON r.id_usuario = u.id
                   WHERE p.id_encuesta = ?''', (id_encuesta,))
    respuestas = cur.fetchall()

    # Calcular promedios por pregunta
    promedios = {}
    for r in respuestas:
        pregunta = r[0]
        valor = r[2]
        if valor is not None:
            if pregunta not in promedios:
                promedios[pregunta] = []
            promedios[pregunta].append(valor)

    labels = list(promedios.keys())
    dataValues = [sum(vals)/len(vals) for vals in promedios.values()]

    conn.close()
    return render_template("resultados.html", encuesta=encuesta, respuestas=respuestas, labels=labels, dataValues=dataValues)

    # ---------- Eliminar encuesta (solo admin) ----------
@app.route("/encuestas/eliminar", methods=["POST"])
@login_required
def eliminar_encuesta():
    if current_user.rol != "administrador":
        flash("No tienes permisos para eliminar encuestas", "danger")
        return redirect(url_for("panel"))
    
     # Tomar el id desde el formulario
    id_encuesta = request.form.get("id_encuesta")
    if id_encuesta:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM encuestas WHERE id=?", (id_encuesta,))
        conn.commit()
        conn.close()
        flash("Encuesta eliminada correctamente.", "success")
    else:
        flash("No se seleccionó ninguna encuesta", "warning")

    return redirect(url_for("panel"))


if __name__=="__main__":
    app.run(debug=True)
