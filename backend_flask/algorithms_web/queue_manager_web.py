from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional

# CORREÇÃO IMPORTANTE: Usar import relativo para subir um nível (para backend_flask)
# e encontrar o módulo database.py.
from .. import database as db_module

class Priority(Enum):
    EMERGENCY = 1
    PCD = 2
    ELDERLY = 3
    NORMAL = 4

class QueueManager:
    def __init__(self):
        self.defined_specialties = [
            'orthodontics',
            'cleaning',
            'extraction',
            'general'
        ]
        # A tabela do banco de dados é criada quando database.py é importado.

    def add_patient(self, name: str, specialty: str, priority: Priority = Priority.NORMAL) -> Optional[Dict[str, Any]]:
        if specialty not in self.defined_specialties:
            raise ValueError(f"Especialidade '{specialty}' não reconhecida. Disponíveis: {self.defined_specialties}")

        arrival_time = datetime.now()
        patient_id = db_module.add_patient_db(name, specialty, priority.value, arrival_time)

        if patient_id is not None:
            return {
                'id': patient_id,
                'name': name,
                'specialty': specialty,
                'priority': priority.value,
                'priority_name': priority.name,
                'arrival_time': arrival_time.isoformat(), 
                'status': 'aguardando'
            }
        return None

    def call_next(self, specialty: str) -> Optional[Dict[str, Any]]:
        if specialty not in self.defined_specialties:
            return None
        
        patient_data_from_db = db_module.call_next_patient_db(specialty)
        
        if patient_data_from_db:
            try:
                priority_enum = Priority(patient_data_from_db['priority'])
                patient_data_from_db['priority_name'] = priority_enum.name
            except ValueError:
                patient_data_from_db['priority_name'] = "DESCONHECIDA"
            
            if isinstance(patient_data_from_db.get('arrival_time'), datetime):
                 patient_data_from_db['arrival_time'] = patient_data_from_db['arrival_time'].isoformat()
            return patient_data_from_db
        return None

    def view_queues(self) -> Dict[str, List[Dict[str, Any]]]:
        all_waiting_from_db = db_module.get_all_waiting_patients_db()
        processed_queues: Dict[str, List[Dict[str, Any]]] = {spec: [] for spec in self.defined_specialties}

        for spec, patients_list in all_waiting_from_db.items():
            if spec in processed_queues:
                for patient_db in patients_list:
                    patient_display = patient_db.copy()
                    try:
                        priority_enum = Priority(patient_db['priority'])
                        patient_display['priority_name'] = priority_enum.name
                    except ValueError:
                        patient_display['priority_name'] = "DESCONHECIDA"
                    
                    if isinstance(patient_display.get('arrival_time'), datetime):
                        patient_display['arrival_time'] = patient_display['arrival_time'].strftime('%d/%m/%Y %H:%M:%S') 
                    
                    processed_queues[spec].append(patient_display)
        return processed_queues

    def get_available_specialties(self) -> list:
        return self.defined_specialties
