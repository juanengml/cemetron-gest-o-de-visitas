from src.database import get_db
from datetime import datetime, timedelta

def get_relatorio_diario():
    """
    Obter relatório de visitas para o dia atual.
    
    Returns:
        list: Lista de visitas do dia atual com dados completos
    """
    hoje = datetime.now().strftime('%Y-%m-%d')
    return get_relatorio_por_periodo(hoje, hoje)

def get_relatorio_por_periodo(data_inicio, data_fim):
    """
    Obter relatório de visitas para um período específico.
    
    Args:
        data_inicio (str): Data inicial no formato 'YYYY-MM-DD'
        data_fim (str): Data final no formato 'YYYY-MM-DD'
    
    Returns:
        list: Lista de visitas no período especificado com dados completos
    """
    db = get_db()
    
    # Ajustar data_fim para incluir todo o dia
    try:
        data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d')
        data_fim_obj = data_fim_obj.replace(hour=23, minute=59, second=59)
        data_fim_completo = data_fim_obj.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        # Se o formato da data não for válido, usar o dia atual
        data_fim_obj = datetime.now().replace(hour=23, minute=59, second=59)
        data_fim_completo = data_fim_obj.strftime('%Y-%m-%d %H:%M:%S')
    
    # Ajustar data_inicio para começar à meia-noite
    try:
        data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d')
        data_inicio_completo = data_inicio_obj.strftime('%Y-%m-%d 00:00:00')
    except ValueError:
        # Se o formato da data não for válido, usar o primeiro dia do mês atual
        hoje = datetime.now()
        data_inicio_obj = datetime(hoje.year, hoje.month, 1)
        data_inicio_completo = data_inicio_obj.strftime('%Y-%m-%d 00:00:00')
    
    query = """
        SELECT v.*, p.nome as patient_name, a.sigla as ward
        FROM visitas v
        JOIN pacientes p ON v.patient_id = p.id
        JOIN alas a ON p.ala_id = a.sigla
        WHERE v.registration_time BETWEEN ? AND ?
        ORDER BY v.registration_time DESC
    """
    
    cursor = db.execute(query, (data_inicio_completo, data_fim_completo))
    visitas = []
    
    for row in cursor.fetchall():
        visita = dict(row)
        
        # Calcular duração da visita para visitas concluídas
        if visita['status'] == 'completed' and visita['start_time'] is not None and visita['end_time'] is not None:
            try:
                # Converter para string se for outro tipo de dado
                start_time_str = visita['start_time'] if isinstance(visita['start_time'], str) else str(visita['start_time'])
                end_time_str = visita['end_time'] if isinstance(visita['end_time'], str) else str(visita['end_time'])
                
                # Tentar converter para datetime
                try:
                    start_time = datetime.fromisoformat(start_time_str)
                except ValueError:
                    # Formato alternativo comum no SQLite
                    start_time = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S')
                
                try:
                    end_time = datetime.fromisoformat(end_time_str)
                except ValueError:
                    # Formato alternativo comum no SQLite
                    end_time = datetime.strptime(end_time_str, '%Y-%m-%d %H:%M:%S')
                
                # Calcular duração
                duracao = (end_time - start_time).total_seconds() / 60  # Duração em minutos
                visita['duracao_minutos'] = round(duracao, 1)
            except (ValueError, TypeError) as e:
                print(f"Erro ao processar datas da visita {visita['id']}: {e}")
                # Definir uma duração padrão para não quebrar a interface
                visita['duracao_minutos'] = 0
        else:
            visita['duracao_minutos'] = 0
        
        visitas.append(visita)
    
    return visitas

def get_estatisticas(relatorio_data):
    """
    Calcular estatísticas a partir dos dados do relatório.
    
    Args:
        relatorio_data (list): Lista de visitas obtida de get_relatorio_por_periodo
    
    Returns:
        dict: Dicionário com diversas estatísticas sobre as visitas
    """
    # Inicializar contadores
    total_visitas = len(relatorio_data)
    visitas_completas = 0
    visitas_ativas = 0
    visitas_espera = 0
    
    # Dicionário para contar visitas por ala
    visitas_por_ala = {}
    
    # Dicionário para calcular tempo médio por ala
    tempo_por_ala = {}
    contagem_por_ala = {}
    
    for visita in relatorio_data:
        # Contar por status
        if visita['status'] == 'completed':
            visitas_completas += 1
        elif visita['status'] == 'active':
            visitas_ativas += 1
        elif visita['status'] == 'waiting':
            visitas_espera += 1
        
        # Contar por ala
        ala = visita['ward']
        if ala in visitas_por_ala:
            visitas_por_ala[ala] += 1
        else:
            visitas_por_ala[ala] = 1
        
        # Calcular tempo para visitas concluídas
        if visita['status'] == 'completed' and 'duracao_minutos' in visita:
            if ala in tempo_por_ala:
                tempo_por_ala[ala] += visita['duracao_minutos']
                contagem_por_ala[ala] += 1
            else:
                tempo_por_ala[ala] = visita['duracao_minutos']
                contagem_por_ala[ala] = 1
    
    # Formatar dados de visitas por ala
    visitas_por_ala_formatado = []
    for ala, quantidade in visitas_por_ala.items():
        percentual = (quantidade / total_visitas * 100) if total_visitas > 0 else 0
        visitas_por_ala_formatado.append({
            'ala': ala,
            'quantidade': quantidade,
            'percentual': round(percentual, 1)
        })
    
    # Ordenar por quantidade (decrescente)
    visitas_por_ala_formatado = sorted(
        visitas_por_ala_formatado, 
        key=lambda x: x['quantidade'], 
        reverse=True
    )
    
    # Calcular tempo médio por ala
    tempo_medio_por_ala = []
    for ala, tempo_total in tempo_por_ala.items():
        tempo_medio = tempo_total / contagem_por_ala[ala]
        tempo_medio_por_ala.append({
            'ala': ala,
            'tempo_medio': round(tempo_medio, 1)
        })
    
    # Ordenar por tempo médio (decrescente)
    tempo_medio_por_ala = sorted(
        tempo_medio_por_ala, 
        key=lambda x: x['tempo_medio'], 
        reverse=True
    )
    
    return {
        'total_visitas': total_visitas,
        'visitas_completas': visitas_completas,
        'visitas_ativas': visitas_ativas,
        'visitas_espera': visitas_espera,
        'visitas_por_ala': visitas_por_ala_formatado,
        'tempo_medio_por_ala': tempo_medio_por_ala
    }