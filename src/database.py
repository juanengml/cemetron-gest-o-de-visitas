import sqlite3
import os
from flask import current_app, g

def get_db():
    """Conectar ao banco de dados SQLite se não houver conexão existente."""
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    
    return g.db

def close_db(e=None):
    """Fechar a conexão com o banco de dados."""
    db = g.pop('db', None)
    
    if db is not None:
        db.close()

def init_db():
    """Inicializar o banco de dados com o esquema definido."""
    db = get_db()
    
    # Verificar se as tabelas já existem
    cursor = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='alas'")
    tables_exist = cursor.fetchone() is not None
    
    if not tables_exist:
        # Se as tabelas não existirem, criar o esquema
        schema = """
        -- Desativar foreign keys temporariamente
        PRAGMA foreign_keys = OFF;

        -- Criação das tabelas
        CREATE TABLE IF NOT EXISTS alas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sigla TEXT UNIQUE NOT NULL,
            nome TEXT NOT NULL,
            descricao TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS pacientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            ala_id TEXT NOT NULL,
            quarto TEXT NOT NULL,
            leito TEXT NOT NULL,
            ativo INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ala_id) REFERENCES alas (sigla)
        );

        CREATE TABLE IF NOT EXISTS visitas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visitor_name TEXT NOT NULL,
            patient_id INTEGER NOT NULL,
            registration_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            start_time TIMESTAMP,
            end_time TIMESTAMP,
            status TEXT DEFAULT 'waiting',  -- waiting, active, completed
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (patient_id) REFERENCES pacientes (id)
        );

        -- Trigger para atualizar o timestamp 'updated_at' quando um registro for atualizado
        CREATE TRIGGER IF NOT EXISTS update_alas_timestamp 
        AFTER UPDATE ON alas
        BEGIN
            UPDATE alas SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
        END;

        CREATE TRIGGER IF NOT EXISTS update_pacientes_timestamp 
        AFTER UPDATE ON pacientes
        BEGIN
            UPDATE pacientes SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
        END;

        CREATE TRIGGER IF NOT EXISTS update_visitas_timestamp 
        AFTER UPDATE ON visitas
        BEGIN
            UPDATE visitas SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
        END;
        """
        
        # Executar o esquema
        db.executescript(schema)
        
        # Inserir dados padrão (alas)
        default_wards = [
            ('Infecto', 'Infectologia', 'Requer uso de EPI completo'),
            ('Viral', 'Virologia', 'Requer uso de máscara e luvas'),
            ('Pediatria', 'Pediatria', 'Atendimento infantil'),
            ('Oncologia', 'Oncologia', 'Tratamento de câncer'),
            ('Cirurgia', 'Cirurgia Geral', 'Pré e pós-operatório'),
            ('UTI', 'Unidade de Terapia Intensiva', 'Cuidados críticos')
        ]
        
        cursor = db.cursor()
        for ward in default_wards:
            cursor.execute(
                "INSERT OR IGNORE INTO alas (sigla, nome, descricao) VALUES (?, ?, ?)",
                ward
            )
        
        db.commit()
        print("Banco de dados inicializado com sucesso!")
    else:
        print("Banco de dados já existe, nenhuma alteração foi feita.")
# Função auxiliar para converter uma linha do banco para dicionário
def dict_factory(cursor, row):
    """Converter uma linha de banco de dados em dicionário."""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d