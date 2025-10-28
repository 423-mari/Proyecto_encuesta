import sqlite3, os, textwrap
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__), 'sistema_encuestas.db')

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = None
    return conn

def initialize_db():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('PRAGMA foreign_keys = ON;')
    cur.executescript(textwrap.dedent("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT,
        correo TEXT UNIQUE,
        password_hash TEXT,
        rol TEXT
    );
    CREATE TABLE IF NOT EXISTS encuestas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        titulo TEXT,
        descripcion TEXT,
        fecha_creacion TEXT
    );
    CREATE TABLE IF NOT EXISTS preguntas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_encuesta INTEGER,
        texto_pregunta TEXT,
        tipo TEXT,
        FOREIGN KEY (id_encuesta) REFERENCES encuestas(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS respuestas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_pregunta INTEGER,
        id_usuario INTEGER,
        respuesta_texto TEXT,
        valor INTEGER,
        FOREIGN KEY (id_pregunta) REFERENCES preguntas(id) ON DELETE CASCADE,
        FOREIGN KEY (id_usuario) REFERENCES usuarios(id) ON DELETE SET NULL
    );
    """))
    cur.execute('SELECT COUNT(*) FROM usuarios')
    cnt = cur.fetchone()[0]
    if cnt == 0:
        cur.execute('INSERT INTO usuarios (nombre, correo, password_hash, rol) VALUES (?,?,?,?)', 
                    ('Administrador', 'admin@demo.com', generate_password_hash('1234'), 'administrador'))
        cur.execute('INSERT INTO usuarios (nombre, correo, password_hash, rol) VALUES (?,?,?,?)', 
                    ('Usuario', 'user@demo.com', generate_password_hash('1234'), 'usuario'))
    conn.commit()
    conn.close()

initialize_db()
