import mysql.connector
from mysql.connector import Error
from datetime import datetime
from typing import List, Dict, Any, Optional

# Suas credenciais e nome do banco de dados
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '@420', # Sua senha
    'database': 'odonto' # Seu banco de dados
}

TABLE_NAME = 'patients'

def get_db_connection() -> Optional[mysql.connector.MySQLConnection]:
    """Estabelece uma conexão com o banco de dados MySQL."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"Erro ao conectar ao banco de dados MySQL: {e}")
        return None
    return None # Garantir que sempre retorne algo ou levante exceção

def create_patients_table():
    """Cria a tabela de pacientes se ela não existir."""
    conn = get_db_connection()
    if not conn:
        print("Falha ao obter conexão com o DB para criar tabela.")
        return

    cursor: Optional[mysql.connector.cursor.MySQLCursor] = None
    try:
        cursor = conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                specialty VARCHAR(100) NOT NULL,
                priority INT NOT NULL,
                arrival_time DATETIME NOT NULL,
                status VARCHAR(50) DEFAULT 'aguardando',
                attended_time DATETIME NULL,
                CONSTRAINT chk_status CHECK (status IN ('aguardando', 'atendido', 'cancelado'))
            ) ENGINE=InnoDB;
        """)
        conn.commit()
        # print(f"Tabela '{TABLE_NAME}' verificada/criada com sucesso.")
    except Error as e:
        print(f"Erro ao criar tabela '{TABLE_NAME}': {e}")
    finally:
        if conn and conn.is_connected():
            if cursor:
                cursor.close()
            conn.close()

def add_patient_db(name: str, specialty: str, priority_value: int, arrival_time: datetime) -> Optional[int]:
    conn = get_db_connection()
    if not conn:
        return None
    
    patient_id = None
    cursor: Optional[mysql.connector.cursor.MySQLCursor] = None
    try:
        cursor = conn.cursor()
        sql = f"INSERT INTO {TABLE_NAME} (name, specialty, priority, arrival_time, status) VALUES (%s, %s, %s, %s, %s)"
        val = (name, specialty, priority_value, arrival_time, 'aguardando')
        cursor.execute(sql, val)
        conn.commit()
        patient_id = cursor.lastrowid
    except Error as e:
        print(f"Erro ao adicionar paciente ao DB: {e}")
    finally:
        if conn and conn.is_connected():
            if cursor: cursor.close()
            conn.close()
    return patient_id

def call_next_patient_db(specialty: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    if not conn: return None

    patient_data = None
    cursor: Optional[mysql.connector.cursor.MySQLCursorDict] = None
    try:
        cursor = conn.cursor(dictionary=True) 
        sql_select = f"SELECT id, name, specialty, priority, arrival_time, status FROM {TABLE_NAME} WHERE specialty = %s AND status = 'aguardando' ORDER BY priority ASC, arrival_time ASC LIMIT 1"
        cursor.execute(sql_select, (specialty,))
        patient_to_call = cursor.fetchone()

        if patient_to_call:
            patient_id = patient_to_call['id']
            sql_update = f"UPDATE {TABLE_NAME} SET status = 'atendido', attended_time = %s WHERE id = %s"
            cursor.execute(sql_update, (datetime.now(), patient_id))
            conn.commit() 
            patient_data = patient_to_call
        else:
            if conn.in_transaction if hasattr(conn, 'in_transaction') else False: conn.rollback() # Adicionado hasattr para segurança
    except Error as e:
        print(f"Erro ao chamar próximo paciente para especialidade '{specialty}': {e}")
        if conn and conn.is_connected() and (conn.in_transaction if hasattr(conn, 'in_transaction') else False): conn.rollback() 
    finally:
        if conn and conn.is_connected():
            if cursor: cursor.close()
            conn.close()
    return patient_data

def get_patients_by_status_and_specialty_db(specialty: str, status: str = 'aguardando') -> List[Dict[str, Any]]:
    conn = get_db_connection()
    if not conn: return []
    
    patients = []
    cursor: Optional[mysql.connector.cursor.MySQLCursorDict] = None
    try:
        cursor = conn.cursor(dictionary=True)
        sql = f"SELECT id, name, specialty, priority, arrival_time, status FROM {TABLE_NAME} WHERE specialty = %s AND status = %s ORDER BY priority ASC, arrival_time ASC"
        cursor.execute(sql, (specialty, status))
        patients = cursor.fetchall()
    except Error as e:
        print(f"Erro ao buscar pacientes para especialidade '{specialty}', status '{status}': {e}")
    finally:
        if conn and conn.is_connected():
            if cursor: cursor.close()
            conn.close()
    return patients

def get_all_waiting_patients_db() -> Dict[str, List[Dict[str, Any]]]:
    conn = get_db_connection()
    if not conn: return {}

    patients_by_specialty: Dict[str, List[Dict[str, Any]]] = {}
    cursor: Optional[mysql.connector.cursor.MySQLCursorDict] = None
    try:
        cursor = conn.cursor(dictionary=True)
        sql = f"SELECT id, name, specialty, priority, arrival_time, status FROM {TABLE_NAME} WHERE status = 'aguardando' ORDER BY specialty ASC, priority ASC, arrival_time ASC"
        cursor.execute(sql)
        all_waiting = cursor.fetchall()
        for patient in all_waiting:
            spec = patient['specialty']
            if spec not in patients_by_specialty:
                patients_by_specialty[spec] = []
            patients_by_specialty[spec].append(patient)
    except Error as e:
        print(f"Erro ao buscar todos os pacientes em espera: {e}")
    finally:
        if conn and conn.is_connected():
            if cursor: cursor.close()
            conn.close()
    return patients_by_specialty

# Chamada para criar a tabela na importação do módulo
try:
    create_patients_table()
except Exception as e:
    print(f"Erro ao tentar criar tabela na importação de database.py: {e}")


if __name__ == '__main__':
    print("Testando database.py...")
    create_patients_table() 
    print("Tabela 'patients' verificada/criada.")
    # Adicione mais testes se necessário
    # add_patient_db("Maria Silva Teste", "general", 1, datetime.now()) 
    # add_patient_db("Joao Costa Teste", "orthodontics", 4, datetime.now())
    # print("Pacientes de teste adicionados.")
