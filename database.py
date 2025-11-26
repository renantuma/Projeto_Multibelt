import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import os

def init_db():
    """Inicializa o banco de dados"""
    conn = sqlite3.connect('usuarios.db')
    cursor = conn.cursor()
    
    # Tabela de usuários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    """Retorna uma conexão com o banco de dados"""
    conn = sqlite3.connect('usuarios.db')
    conn.row_factory = sqlite3.Row
    return conn

class Usuario:
    def __init__(self, username, email, password_hash=None, id=None):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
    
    @staticmethod
    def criar_usuario(username, email, password):
        """Cria um novo usuário no banco de dados"""
        password_hash = generate_password_hash(password)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                'INSERT INTO usuarios (username, email, password_hash) VALUES (?, ?, ?)',
                (username, email, password_hash)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False  # Usuário ou email já existe
        finally:
            conn.close()
    
    @staticmethod
    def buscar_por_username(username):
        """Busca usuário pelo username"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM usuarios WHERE username = ?', (username,))
        usuario_data = cursor.fetchone()
        conn.close()
        
        if usuario_data:
            return Usuario(
                id=usuario_data['id'],
                username=usuario_data['username'],
                email=usuario_data['email'],
                password_hash=usuario_data['password_hash']
            )
        return None
    
    @staticmethod
    def buscar_por_email(email):
        """Busca usuário pelo email"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM usuarios WHERE email = ?', (email,))
        usuario_data = cursor.fetchone()
        conn.close()
        
        if usuario_data:
            return Usuario(
                id=usuario_data['id'],
                username=usuario_data['username'],
                email=usuario_data['email'],
                password_hash=usuario_data['password_hash']
            )
        return None
    
    def verificar_senha(self, password):
        """Verifica se a senha está correta"""
        return check_password_hash(self.password_hash, password)