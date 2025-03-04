import sqlite3
import os
from datetime import datetime, timedelta

# Configurações do banco de dados
DB_PATH = 'instance/cemetrom.db'
DATA_ATUAL = datetime(2025, 3, 3)  # 03/03/2025

print(f"Executando script de seeds para {DATA_ATUAL.strftime('%d/%m/%Y')}")

# Verificar se o banco de dados existe
if not os.path.exists(DB_PATH):
    print(f"Erro: Banco de dados não encontrado em {DB_PATH}")
    print("Execute a aplicação principal primeiro para criar o banco de dados.")
    exit(1)

# Conectar ao banco de dados
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Verificar tabelas existentes
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('alas', 'pacientes', 'visitas')")
tabelas = cursor.fetchall()
tabelas_existentes = [tabela[0] for tabela in tabelas]

print(f"Tabelas encontradas: {', '.join(tabelas_existentes)}")

# Limpar dados existentes (para evitar duplicações)
cursor.execute("DELETE FROM visitas")
cursor.execute("DELETE FROM pacientes")
cursor.execute("DELETE FROM alas")
conn.commit()
print("Dados existentes foram limpos.")

# 1. Criar alas (básico: apenas 3 alas)
alas = [
    ('Infecto', 'Infectologia', 'Requer uso de EPI completo'),
    ('Pediatria', 'Pediatria', 'Atendimento infantil'),
    ('UTI Cardio e Adulto', 'Unidade de Terapia Intensiva', 'Cuidados críticos'),
    ('Clinica Feminina', 'Unidade Feminina', 'Cuidados Femininos'),
    ('Clinica Masculina', 'Unidade Masculina', 'Cuidados Masculina')
]

print("\nInserindo alas:")
for ala in alas:
    cursor.execute(
        "INSERT INTO alas (sigla, nome, descricao) VALUES (?, ?, ?)",
        ala
    )
    print(f"  • {ala[0]}: {ala[1]}")

conn.commit()

# 2. Criar pacientes (5 pacientes)
pacientes = [
    ("João Silva", "UTI Cardio e Adulto", "101", "A"),
    ("Maria Oliveira", "Pediatria", "201", "B"),
    ("José Santos", "Infecto", "301", "A"),
    ("Ana Pereira", "UTI Cardio e Adulto", "102", "C"),
    ("Carlos Ferreira", "Pediatria", "202", "A")
]

print("\nInserindo pacientes:")
pacientes_ids = []
for paciente in pacientes:
    cursor.execute(
        """
        INSERT INTO pacientes (nome, ala_id, quarto, leito, ativo)
        VALUES (?, ?, ?, ?, 1)
        """,
        paciente
    )
    paciente_id = cursor.lastrowid
    pacientes_ids.append(paciente_id)
    print(f"  • ID {paciente_id}: {paciente[0]} - Ala: {paciente[1]}, Quarto: {paciente[2]}, Leito: {paciente[3]}")

conn.commit()

# 3. Criar visitas (4 visitas: 1 concluída, 1 ativa, 2 em espera)
agora = DATA_ATUAL.replace(hour=14, minute=30)  # 14:30

# Uma visita concluída (mais cedo hoje)
inicio_concluida = DATA_ATUAL.replace(hour=10, minute=15)
fim_concluida = inicio_concluida + timedelta(minutes=25)
registro_concluida = inicio_concluida - timedelta(minutes=10)

# Uma visita ativa (em andamento)
inicio_ativa = agora - timedelta(minutes=15)
fim_ativa = inicio_ativa + timedelta(minutes=30)
registro_ativa = inicio_ativa - timedelta(minutes=10)

# Duas visitas em espera
registro_espera1 = agora - timedelta(minutes=45)
registro_espera2 = agora - timedelta(minutes=20)

visitas = [
    # Visita concluída
    ("Pedro Alves", pacientes_ids[0], "completed", 
     registro_concluida.strftime("%Y-%m-%d %H:%M:%S"),
     inicio_concluida.strftime("%Y-%m-%d %H:%M:%S"),
     fim_concluida.strftime("%Y-%m-%d %H:%M:%S")),
     
    # Visita ativa
    ("Mariana Dias", pacientes_ids[1], "active",
     registro_ativa.strftime("%Y-%m-%d %H:%M:%S"),
     inicio_ativa.strftime("%Y-%m-%d %H:%M:%S"),
     fim_ativa.strftime("%Y-%m-%d %H:%M:%S")),
     
    # Visitas em espera
    ("Lucas Ramos", pacientes_ids[2], "waiting",
     registro_espera1.strftime("%Y-%m-%d %H:%M:%S"),
     None, None),
     
    ("Isabela Freitas", pacientes_ids[3], "waiting",
     registro_espera2.strftime("%Y-%m-%d %H:%M:%S"),
     None, None)
]

print("\nInserindo visitas:")
for i, visita in enumerate(visitas):
    cursor.execute(
        """
        INSERT INTO visitas 
        (visitor_name, patient_id, status, registration_time, start_time, end_time)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        visita
    )
    status_desc = {
        "completed": "Concluída",
        "active": "Em andamento",
        "waiting": "Em espera"
    }
    print(f"  • Visita {i+1}: {visita[0]} → Paciente ID {visita[1]} ({status_desc[visita[2]]})")

conn.commit()

# Fechar conexão com o banco de dados
conn.close()

print("\n✅ Seed concluído com sucesso!")
print(f"  • {len(alas)} alas inseridas")
print(f"  • {len(pacientes)} pacientes inseridos")
print(f"  • {len(visitas)} visitas inseridas")
print("\nVocê pode iniciar a aplicação agora com 'python app.py'")