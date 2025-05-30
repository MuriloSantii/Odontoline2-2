import sys
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime

# REMOVIDA a manipulação explícita de sys.path daqui.
# O comando "python -m backend_flask.app_flask" a partir de Odontoline2/
# deve configurar o sys.path corretamente.

try:
    # Imports relativos ao pacote atual (backend_flask)
    from .algorithms_web.queue_manager_web import QueueManager, Priority
    from . import database 
except ImportError as e:
    print(f"--- ERRO DE IMPORTAÇÃO NO app_flask.py ---")
    print(f"Detalhes do erro: {e}")
    print(f"Verifique a estrutura de pastas e se todos os arquivos __init__.py existem:")
    print(f"  - Odontoline2/backend_flask/__init__.py (VAZIO)")
    print(f"  - Odontoline2/backend_flask/algorithms_web/__init__.py (VAZIO)")
    print(f"Certifique-se de estar executando o comando 'python -m backend_flask.app_flask' a partir da pasta 'Odontoline2'.")
    # A linha abaixo pode não ser útil aqui, pois CURRENT_DIR não está mais sendo adicionada ao sys.path por este script
    # print(f"Caminho que seria adicionado ao sys.path (se existisse): {Path(__file__).resolve().parent}")
    print(f"Conteúdo do sys.path (primeiros caminhos): {sys.path[:7]}")
    sys.exit(1)

# Define o caminho para a pasta frontend_web
CURRENT_DIR_OF_APP_FLASK = Path(__file__).resolve().parent # backend_flask/
APP_ROOT_DIR = CURRENT_DIR_OF_APP_FLASK.parent  # Odontoline2/
FRONTEND_FOLDER_PATH = APP_ROOT_DIR / 'frontend_web'

app = Flask(__name__,
            static_folder=str(FRONTEND_FOLDER_PATH),
            static_url_path='')
CORS(app)

try:
    qm = QueueManager()
except Exception as e:
    print(f"--- ERRO AO INICIALIZAR QueueManager: {e} ---")
    print("Verifique a conexão com o banco de dados em 'database.py' (DB_CONFIG).")
    sys.exit(1)

# --- Endpoints da API ---
@app.route('/')
def serve_index_html():
    try:
        if not Path(app.static_folder).exists():
            app.logger.error(f"ERRO: Pasta estática não encontrada em {app.static_folder}")
            return "Erro de configuração do servidor: pasta frontend não encontrada.", 500
        if not (Path(app.static_folder) / 'index.html').exists():
            app.logger.error(f"ERRO: index.html não encontrado em {Path(app.static_folder) / 'index.html'}")
            return "Erro de configuração do servidor: index.html não encontrado.", 500
        return send_from_directory(app.static_folder, 'index.html')
    except Exception as e:
        app.logger.error(f"Erro ao servir index.html: {e}", exc_info=True)
        return "Erro ao carregar página principal.", 500

@app.route('/api/adicionar_paciente', methods=['POST']) 
def api_add_patient():
    try:
        data = request.get_json()
        if not data or not all(k in data for k in ['nome', 'specialty', 'priority']):
            return jsonify({"error": "Dados incompletos: 'nome', 'specialty', 'priority' são obrigatórios."}), 400

        name = data['nome']
        specialty = data['specialty']
        
        try:
            priority_value = int(data['priority'])
            priority_enum = Priority(priority_value)
        except ValueError:
            return jsonify({"error": "Valor de prioridade inválido."}), 400
        except KeyError:
             return jsonify({"error": "Chave 'priority' não encontrada."}), 400

        if specialty not in qm.get_available_specialties():
             return jsonify({"error": f"Especialidade '{specialty}' não reconhecida."}), 400

        patient_added_dict = qm.add_patient(name, specialty, priority_enum)

        if patient_added_dict:
            return jsonify({"message": "Paciente adicionado com sucesso!", "patient": patient_added_dict}), 201
        else:
            return jsonify({"error": "Falha ao adicionar paciente (verifique logs)."}), 500

    except Exception as e:
        app.logger.error(f"Erro em POST /api/adicionar_paciente: {e}", exc_info=True)
        return jsonify({"error": "Erro interno no servidor ao adicionar paciente."}), 500

@app.route('/api/filas', methods=['GET'])
def api_get_queues():
    try:
        queues_data = qm.view_queues()
        return jsonify(queues_data), 200
    except Exception as e:
        app.logger.error(f"Erro em GET /api/filas: {e}", exc_info=True)
        return jsonify({"error": "Erro interno ao buscar filas."}), 500

@app.route('/api/chamar_proximo', methods=['POST'])
def api_call_next():
    try:
        data = request.get_json()
        if not data or 'specialty' not in data:
            return jsonify({"error": "Especialidade é obrigatória."}), 400
        specialty = data['specialty']
        if specialty not in qm.get_available_specialties():
             return jsonify({"error": f"Especialidade '{specialty}' não reconhecida."}), 400
        patient_called_dict = qm.call_next(specialty)
        if patient_called_dict:
            return jsonify({"message": "Próximo paciente chamado!", "patient": patient_called_dict}), 200
        else:
            return jsonify({"message": f"Nenhum paciente na fila para '{specialty}'."}), 200
    except Exception as e:
        app.logger.error(f"Erro em POST /api/chamar_proximo: {e}", exc_info=True)
        return jsonify({"error": "Erro interno ao chamar próximo."}), 500

if __name__ == '__main__':
    print("--- Iniciando Servidor Flask OdontoLine ---")
    print("Verificando conexão com o banco de dados...")
    try:
        conn_test = database.get_db_connection()
        if conn_test and conn_test.is_connected():
            print(">>> Conexão com o banco de dados MySQL ('odonto') bem-sucedida.")
            conn_test.close()
            print(f">>> Tabela '{database.TABLE_NAME}' no banco '{database.DB_CONFIG['database']}' pronta.")
        else:
            print(">>> ERRO CRÍTICO: Falha ao conectar ao MySQL.")
            # CURRENT_DIR_OF_APP_FLASK é backend_flask/
            print(f"    Verifique credenciais em '{CURRENT_DIR_OF_APP_FLASK / 'database.py'}' e se o servidor MySQL está rodando.")
            sys.exit(1)
    except Exception as e_db_test:
        print(f">>> ERRO CRÍTICO no teste de conexão com DB: {e_db_test}")
        sys.exit(1)
    
    PORT = 5001
    print(f"Servidor Flask rodando na porta {PORT}.")
    print(f"Acesse a aplicação em: http://127.0.0.1:{PORT}/")
    app.run(debug=True, host='0.0.0.0', port=PORT)
