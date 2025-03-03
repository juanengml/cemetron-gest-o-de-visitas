from src.database import get_db
from datetime import datetime

def get_pacientes(only_active=True):
    """
    Obter lista de pacientes do banco de dados.
    
    Args:
        only_active (bool, optional): Filtrar apenas pacientes ativos
    
    Returns:
        list: Lista de pacientes em formato de dicionário
    """
    db = get_db()
    query = """
        SELECT p.*, a.nome as ala_nome, a.descricao as ala_descricao
        FROM pacientes p
        JOIN alas a ON p.ala_id = a.sigla
    """
    
    params = []
    
    if only_active:
        query += " WHERE p.ativo = 1"
    
    query += " ORDER BY p.nome"
    
    cursor = db.execute(query, params)
    pacientes = []
    
    for row in cursor.fetchall():
        pacientes.append(dict(row))
    
    return pacientes

def get_paciente_by_id(paciente_id):
    """
    Obter um paciente específico pelo ID.
    
    Args:
        paciente_id (int): ID do paciente
    
    Returns:
        dict: Informações do paciente ou None se não encontrado
    """
    db = get_db()
    cursor = db.execute(
        """
        SELECT p.*, a.nome as ala_nome, a.descricao as ala_descricao
        FROM pacientes p
        JOIN alas a ON p.ala_id = a.sigla
        WHERE p.id = ?
        """,
        (paciente_id,)
    )
    
    paciente = cursor.fetchone()
    
    if paciente:
        return dict(paciente)
    
    return None

def verificar_ala_existe(ala_id):
    """
    Verificar se uma ala existe no banco de dados.
    
    Args:
        ala_id (str): Sigla da ala
    
    Returns:
        bool: True se a ala existe, False caso contrário
    """
    db = get_db()
    cursor = db.execute(
        "SELECT id FROM alas WHERE sigla = ?",
        (ala_id,)
    )
    
    return cursor.fetchone() is not None

def verificar_leito_ocupado(ala_id, quarto, leito, paciente_id=None):
    """
    Verificar se um leito já está ocupado por outro paciente.
    
    Args:
        ala_id (str): Sigla da ala
        quarto (str): Número do quarto
        leito (str): Identificação do leito
        paciente_id (int, optional): ID do paciente atual (para edição)
    
    Returns:
        bool: True se o leito estiver ocupado, False caso contrário
    """
    db = get_db()
    query = """
        SELECT id FROM pacientes
        WHERE ala_id = ? AND quarto = ? AND leito = ? AND ativo = 1
    """
    
    params = [ala_id, quarto, leito]
    
    if paciente_id:
        query += " AND id != ?"
        params.append(paciente_id)
    
    cursor = db.execute(query, params)
    
    return cursor.fetchone() is not None

def criar_paciente(nome, ala_id, quarto, leito):
    """
    Cadastrar um novo paciente.
    
    Args:
        nome (str): Nome do paciente
        ala_id (str): Sigla da ala (ex: "UTI")
        quarto (str): Número do quarto
        leito (str): Identificação do leito
    
    Returns:
        int or str: ID do paciente criado ou mensagem de erro
    """
    # Verificar se a ala existe
    if not verificar_ala_existe(ala_id):
        return f"A ala {ala_id} não existe."
    
    # Verificar se já existe paciente no mesmo quarto/leito
    if verificar_leito_ocupado(ala_id, quarto, leito):
        return f"O leito {leito} do quarto {quarto} na ala {ala_id} já está ocupado."
    
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO pacientes (nome, ala_id, quarto, leito, ativo)
        VALUES (?, ?, ?, ?, 1)
        """,
        (nome, ala_id, quarto, leito)
    )
    
    db.commit()
    return cursor.lastrowid

def atualizar_paciente(paciente_id, nome, ala_id, quarto, leito):
    """
    Atualizar dados de um paciente existente.
    
    Args:
        paciente_id (int): ID do paciente
        nome (str): Nome do paciente
        ala_id (str): Sigla da ala
        quarto (str): Número do quarto
        leito (str): Identificação do leito
    
    Returns:
        bool or str: True se sucesso ou mensagem de erro
    """
    # Verificar se o paciente existe
    paciente = get_paciente_by_id(paciente_id)
    if not paciente:
        return "Paciente não encontrado."
    
    # Verificar se a ala existe
    if not verificar_ala_existe(ala_id):
        return f"A ala {ala_id} não existe."
    
    # Verificar se já existe outro paciente no mesmo quarto/leito
    if verificar_leito_ocupado(ala_id, quarto, leito, paciente_id):
        return f"O leito {leito} do quarto {quarto} na ala {ala_id} já está ocupado."
    
    db = get_db()
    db.execute(
        """
        UPDATE pacientes
        SET nome = ?, ala_id = ?, quarto = ?, leito = ?
        WHERE id = ?
        """,
        (nome, ala_id, quarto, leito, paciente_id)
    )
    
    db.commit()
    return True

def deletar_paciente(paciente_id):
    """
    Desativar um paciente (soft delete).
    
    Args:
        paciente_id (int): ID do paciente
    
    Returns:
        bool or str: True se sucesso ou mensagem de erro
    """
    # Verificar se o paciente existe
    paciente = get_paciente_by_id(paciente_id)
    if not paciente:
        return "Paciente não encontrado."
    
    # Verificar se há visitas ativas para este paciente
    db = get_db()
    cursor = db.execute(
        """
        SELECT id FROM visitas
        WHERE patient_id = ? AND status IN ('waiting', 'active')
        LIMIT 1
        """,
        (paciente_id,)
    )
    
    if cursor.fetchone():
        return "Não é possível remover o paciente pois há visitas pendentes ou ativas para ele."
    
    # Desativar o paciente (soft delete)
    db.execute(
        """
        UPDATE pacientes
        SET ativo = 0
        WHERE id = ?
        """,
        (paciente_id,)
    )
    
    db.commit()
    return True

def get_alas():
    """
    Obter lista de todas as alas disponíveis.
    
    Returns:
        list: Lista de alas em formato de dicionário
    """
    db = get_db()
    cursor = db.execute(
        """
        SELECT * FROM alas
        ORDER BY nome
        """
    )
    
    alas = []
    for row in cursor.fetchall():
        alas.append(dict(row))
    
    return alas

def get_estatisticas_pacientes():
    """
    Obter estatísticas sobre os pacientes.
    
    Returns:
        dict: Estatísticas sobre pacientes
    """
    db = get_db()
    
    # Total de pacientes ativos
    cursor = db.execute("SELECT COUNT(*) as total FROM pacientes WHERE ativo = 1")
    total_pacientes = cursor.fetchone()['total']
    
    # Pacientes por ala
    cursor = db.execute("""
        SELECT a.sigla, a.nome, COUNT(p.id) as count
        FROM alas a
        LEFT JOIN pacientes p ON a.sigla = p.ala_id AND p.ativo = 1
        GROUP BY a.sigla, a.nome
        ORDER BY count DESC
    """)
    
    pacientes_por_ala = []
    for row in cursor.fetchall():
        pacientes_por_ala.append(dict(row))
    
    return {
        'total_pacientes': total_pacientes,
        'pacientes_por_ala': pacientes_por_ala
    }