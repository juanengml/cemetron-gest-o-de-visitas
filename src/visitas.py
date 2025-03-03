from datetime import datetime, timedelta
from src.database import get_db
from src.pacientes import get_paciente_by_id

def get_visitas(status=None, limit=None):
    """
    Obter lista de visitas do banco de dados.
    
    Args:
        status (str, optional): Filtrar por status (waiting, active, completed)
        limit (int, optional): Limitar o número de resultados
    
    Returns:
        list: Lista de visitas em formato de dicionário
    """
    db = get_db()
    query = """
        SELECT v.*, p.nome as patient_name, a.sigla as ward
        FROM visitas v
        JOIN pacientes p ON v.patient_id = p.id
        JOIN alas a ON p.ala_id = a.sigla
    """
    
    params = []
    
    if status:
        query += " WHERE v.status = ?"
        params.append(status)
    
    query += " ORDER BY v.registration_time DESC"
    
    if limit:
        query += " LIMIT ?"
        params.append(limit)
    
    cursor = db.execute(query, params)
    visitas = []
    
    for row in cursor.fetchall():
        visita = dict(row)
        
        # Adicionar informações de tempo restante para visitas ativas
        if visita['status'] == 'active' and visita['end_time']:
            end_time = datetime.fromisoformat(visita['end_time'])
            now = datetime.now()
            remaining = (end_time - now).total_seconds()
            visita['remaining_seconds'] = max(0, remaining)
            
            # Formatação para exibição
            minutes, seconds = divmod(int(remaining), 60)
            visita['remaining_formatted'] = f"{minutes}:{seconds:02d}"
            
            # Classe CSS baseada no tempo restante
            if remaining <= 0:
                visita['status_class'] = "expired"
            elif remaining < 300:  # Menos de 5 minutos
                visita['status_class'] = "warning"
            else:
                visita['status_class'] = "normal"
        
        visitas.append(visita)
    
    return visitas

def get_visita_by_id(visita_id):
    """
    Obter uma visita específica pelo ID.
    
    Args:
        visita_id (int): ID da visita
    
    Returns:
        dict: Informações da visita ou None se não encontrada
    """
    db = get_db()
    cursor = db.execute(
        """
        SELECT v.*, p.nome as patient_name, a.sigla as ward
        FROM visitas v
        JOIN pacientes p ON v.patient_id = p.id
        JOIN alas a ON p.ala_id = a.sigla
        WHERE v.id = ?
        """,
        (visita_id,)
    )
    
    visita = cursor.fetchone()
    
    if visita:
        return dict(visita)
    
    return None

def contar_visitas_paciente_hoje(patient_id):
    """
    Contar quantas visitas um paciente recebeu hoje.
    
    Args:
        patient_id (int): ID do paciente
    
    Returns:
        int: Número de visitas hoje
    """
    db = get_db()
    today = datetime.now().strftime('%Y-%m-%d')
    
    cursor = db.execute(
        """
        SELECT COUNT(*) as count
        FROM visitas
        WHERE patient_id = ?
        AND DATE(registration_time) = ?
        """,
        (patient_id, today)
    )
    
    result = cursor.fetchone()
    return result['count']

def criar_visita(visitor_name, patient_id, ward):
    """
    Registrar uma nova visita.
    
    Args:
        visitor_name (str): Nome do visitante
        patient_id (int): ID do paciente
        ward (str): Ala do hospital
    
    Returns:
        int or str: ID da visita criada ou mensagem de erro
    """
    # Verificar se o paciente existe
    paciente = get_paciente_by_id(patient_id)
    if not paciente:
        return "Paciente não encontrado."
    
    # Verificar se o paciente está na ala informada
    if paciente['ala_id'] != ward:
        return f"O paciente está na ala {paciente['ala_id']}, não na ala {ward}."
    
    # Verificar limite de visitas por paciente (3 por dia)
    visitas_hoje = contar_visitas_paciente_hoje(patient_id)
    if visitas_hoje >= 3:
        return f"O paciente já atingiu o limite de 3 visitas hoje."
    
    db = get_db()
    cursor = db.execute(
        """
        INSERT INTO visitas (visitor_name, patient_id, status, registration_time)
        VALUES (?, ?, 'waiting', CURRENT_TIMESTAMP)
        """,
        (visitor_name, patient_id)
    )
    
    db.commit()
    return cursor.lastrowid

def iniciar_visita(visita_id):
    """
    Iniciar uma visita que está em espera.
    
    Args:
        visita_id (int): ID da visita
    
    Returns:
        bool or str: True se sucesso ou mensagem de erro
    """
    # Verificar se a visita existe e está em espera
    visita = get_visita_by_id(visita_id)
    if not visita:
        return "Visita não encontrada."
    
    if visita['status'] != 'waiting':
        return f"A visita não pode ser iniciada pois está com status '{visita['status']}'."
    
    # Definir horário de início e fim (30 minutos após o início)
    now = datetime.now()
    end_time = now + timedelta(minutes=30)
    
    db = get_db()
    db.execute(
        """
        UPDATE visitas
        SET status = 'active', start_time = ?, end_time = ?
        WHERE id = ?
        """,
        (now.isoformat(), end_time.isoformat(), visita_id)
    )
    
    db.commit()
    return True

def finalizar_visita(visita_id):
    """
    Finalizar uma visita ativa.
    
    Args:
        visita_id (int): ID da visita
    
    Returns:
        bool or str: True se sucesso ou mensagem de erro
    """
    # Verificar se a visita existe e está ativa
    visita = get_visita_by_id(visita_id)
    if not visita:
        return "Visita não encontrada."
    
    if visita['status'] != 'active':
        return f"A visita não pode ser finalizada pois está com status '{visita['status']}'."
    
    # Definir horário de fim como agora
    now = datetime.now()
    
    db = get_db()
    db.execute(
        """
        UPDATE visitas
        SET status = 'completed', end_time = ?
        WHERE id = ?
        """,
        (now.isoformat(), visita_id)
    )
    
    db.commit()
    return True

def get_visitas_ativas():
    """
    Obter todas as visitas ativas no momento.
    
    Returns:
        list: Lista de visitas ativas
    """
    return get_visitas(status='active')

def limpar_visitas_expiradas():
    """
    Atualizar status de visitas cujo tempo expirou.
    
    Returns:
        int: Número de visitas atualizadas
    """
    db = get_db()
    now = datetime.now().isoformat()
    
    cursor = db.execute(
        """
        UPDATE visitas
        SET status = 'completed'
        WHERE status = 'active'
        AND end_time < ?
        """,
        (now,)
    )
    
    db.commit()
    return cursor.rowcount