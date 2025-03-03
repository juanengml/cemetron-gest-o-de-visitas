from flask import Flask, render_template, redirect, url_for, request, flash, jsonify
from src.database import init_db, get_db, close_db
from src.visitas import (
    get_visitas, get_visita_by_id, criar_visita, 
    iniciar_visita, finalizar_visita, get_visitas_ativas
)
from src.pacientes import (
    get_pacientes, get_paciente_by_id, criar_paciente, 
    atualizar_paciente, deletar_paciente, get_alas
)
from src.relatorio import (
    get_relatorio_diario, get_relatorio_por_periodo, 
    get_estatisticas
)
import os
from datetime import datetime

# Inicializar a aplicação Flask
app = Flask(__name__)
app.secret_key = 'cemetrom_secret_key_2025'  # Chave para sessions e flash messages
app.config['DATABASE'] = os.path.join(app.instance_path, 'cemetrom.db')

# Garantir que a pasta instance exista
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

# Registrar funções para manipulação do banco de dados
app.teardown_appcontext(close_db)

# Criar função de inicialização que será chamada manualmente
def init_app_db():
    with app.app_context():
        init_db()

# Filtros personalizados Jinja para formatação de tempo e datas
@app.template_filter('format_datetime')
def format_datetime(value):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    return value.strftime('%d/%m/%Y %H:%M')

@app.template_filter('format_time')
def format_time(value):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    return value.strftime('%H:%M')

@app.template_filter('time_remaining')
def time_remaining(end_time):
    if isinstance(value, str):
        try:
            end_time = datetime.fromisoformat(end_time)
        except ValueError:
            return "Formato inválido"
    
    now = datetime.now()
    remaining = end_time - now
    
    if remaining.total_seconds() <= 0:
        return "Tempo esgotado"
    
    minutes, seconds = divmod(int(remaining.total_seconds()), 60)
    return f"{minutes}:{seconds:02d}"

@app.template_filter('time_remaining_class')
def time_remaining_class(end_time):
    if isinstance(end_time, str):
        try:
            end_time = datetime.fromisoformat(end_time)
        except ValueError:
            return "invalid"
            
    now = datetime.now()
    remaining = (end_time - now).total_seconds()
    
    if remaining <= 0:
        return "expired"
    elif remaining < 300:  # Menos de 5 minutos
        return "warning"
    else:
        return "normal"

# Rotas para a aplicação
@app.route('/')
def index():
    # Redirecionar para a página de formulário de visitas
    return redirect(url_for('form_visitas'))

# Rotas para visitas
@app.route('/visitas', methods=['GET', 'POST'])
def form_visitas():
    if request.method == 'POST':
        visitor_name = request.form.get('visitor_name')
        patient_id = request.form.get('patient_id')
        ward = request.form.get('ward')
        
        # Validações
        if not visitor_name or not patient_id or not ward:
            flash('Todos os campos são obrigatórios!', 'danger')
            return redirect(url_for('form_visitas'))
        
        result = criar_visita(visitor_name, patient_id, ward)
        if isinstance(result, str):
            flash(result, 'warning')
        else:
            flash('Visita registrada com sucesso!', 'success')
        
        return redirect(url_for('form_visitas'))
    
    # GET request
    visitas_ativas = get_visitas_ativas()
    visitas_espera = get_visitas(status='waiting')
    pacientes = get_pacientes()
    alas = get_alas()
    
    return render_template('form_visitas.html', 
                          visitas_ativas=visitas_ativas,
                          visitas_espera=visitas_espera,
                          pacientes=pacientes,
                          alas=alas)

@app.route('/visitas/iniciar/<int:id>')
def iniciar_visita_route(id):
    resultado = iniciar_visita(id)
    
    if isinstance(resultado, str):
        flash(resultado, 'warning')
    else:
        flash('Visita iniciada com sucesso!', 'success')
    
    return redirect(url_for('form_visitas'))

@app.route('/visitas/finalizar/<int:id>')
def finalizar_visita_route(id):
    resultado = finalizar_visita(id)
    
    if isinstance(resultado, str):
        flash(resultado, 'warning')
    else:
        flash('Visita finalizada com sucesso!', 'success')
    
    return redirect(url_for('form_visitas'))

# Rotas para pacientes
@app.route('/pacientes', methods=['GET', 'POST'])
def form_pacientes():
    if request.method == 'POST':
        # Obter dados do formulário
        name = request.form.get('name')
        ward = request.form.get('ward')
        room = request.form.get('room')
        bed = request.form.get('bed')
        
        # Verificar operação (criar ou atualizar)
        patient_id = request.form.get('patient_id')
        
        if patient_id:  # Atualização de paciente existente
            result = atualizar_paciente(patient_id, name, ward, room, bed)
            flash('Paciente atualizado com sucesso!', 'success')
        else:  # Criação de novo paciente
            result = criar_paciente(name, ward, room, bed)
            flash('Paciente cadastrado com sucesso!', 'success')
        
        return redirect(url_for('form_pacientes'))
    
    # GET request
    pacientes = get_pacientes()
    alas = get_alas()
    
    # Verificar se há um ID de paciente para edição
    patient_id = request.args.get('edit')
    paciente_edit = None
    
    if patient_id:
        paciente_edit = get_paciente_by_id(patient_id)
    
    return render_template('form_pacientes.html', 
                          pacientes=pacientes,
                          alas=alas,
                          paciente_edit=paciente_edit)

@app.route('/pacientes/delete/<int:id>')
def deletar_paciente_route(id):
    resultado = deletar_paciente(id)
    
    if isinstance(resultado, str):
        flash(resultado, 'warning')
    else:
        flash('Paciente removido com sucesso!', 'success')
    
    return redirect(url_for('form_pacientes'))

# Rotas para relatórios
@app.route('/relatorio')
def relatorio():
    # Obter parâmetros de filtro
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    if data_inicio and data_fim:
        relatorio_data = get_relatorio_por_periodo(data_inicio, data_fim)
    else:
        relatorio_data = get_relatorio_diario()
    
    estatisticas = get_estatisticas(relatorio_data)
    
    return render_template('relatorio.html', 
                          relatorio=relatorio_data,
                          estatisticas=estatisticas,
                          data_inicio=data_inicio,
                          data_fim=data_fim)

# API para atualização das visitas ativas via AJAX
@app.route('/api/visitas-ativas')
def api_visitas_ativas():
    visitas_ativas = get_visitas_ativas()
    return jsonify(visitas_ativas)

if __name__ == '__main__':
    # Inicializar o banco de dados antes de executar a aplicação
    init_app_db()
    app.run(debug=True, host="0.0.0.0")