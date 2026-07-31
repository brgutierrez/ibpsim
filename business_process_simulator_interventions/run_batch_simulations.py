"""
Wrapper para ejecutar múltiples simulaciones con la misma configuración de intervenciones.

Este script permite ejecutar N simulaciones sin necesidad de usar la GUI,
almacenando cada log resultante en una carpeta diferente dentro de caseStudy/logDinamico.
"""

import os
import random
import sys
import time
from datetime import date
from pathlib import Path
from dotenv import load_dotenv

from business_process_simulator_interventions.data.data_reader import ShipcallManager
from business_process_simulator_interventions.data.simulation_model import ModelLogSimulation
from business_process_simulator_interventions.config.interventions_config import create_interventions_from_csv_files
from business_process_simulator_interventions.interventions.external_agent.planner import get_vessels_schedule
from business_process_simulator_interventions.interventions.intervention_factory import InterventionsFactory
from business_process_simulator_interventions.simulation.simulation import simulate

load_dotenv()

random.seed(time.time())


def create_output_folder(folder_number):
    """
    Crea la carpeta de salida si no existe.

    Args:
        folder_number: Número de la carpeta (1-30)
    """
    folder_path = Path(f'./caseStudy/logDinamico/{folder_number}')
    folder_path.mkdir(parents=True, exist_ok=True)
    return folder_path


def run_single_simulation(folder_number, interventions_config):
    """
    Ejecuta una simulación individual y guarda los resultados en la carpeta especificada.

    Args:
        folder_number: Número de carpeta donde guardar los resultados
        interventions_config: Diccionario con la configuración de intervenciones
                             (en el formato esperado por InterventionsFactory)
    """
    print(f"\n{'='*80}")
    print(f"Ejecutando simulación #{folder_number}")
    print(f"{'='*80}")

    # Crear carpeta de salida
    create_output_folder(folder_number)

    # Crear modelo de simulación para arrivals
    arrivals_modellogsimul = ModelLogSimulation(
        os.getenv('PROCESS_MODEL'),
        os.getenv('ACTIVITIES_DURATION'),
        os.getenv('ACTIVITIES_RESOURCES'),
        os.getenv('ACTIVITIES_GATEWAYS_PERCENTAGES')
    )

    # Asignar la factory de intervenciones
    # interventions_config es el diccionario collected_data que espera InterventionsFactory
    arrivals_modellogsimul.interventions_factory = InterventionsFactory(interventions_config)

    # Gestionar shipcalls
    unfinished_shipcalls = []
    sh_manager = ShipcallManager()
    dates_to_simulate = sh_manager.get_all_shipcalls_dates()
    dates_to_simulate = [d.strftime('%m/%d/%Y %H:%M:%S') for d in dates_to_simulate]

    LIMIT = 20
    total_processed_shipcalls = 0

    # Simular para cada fecha
    for date_to_plan in dates_to_simulate:

        if total_processed_shipcalls >= LIMIT:
            break

        arrivals_sh_to_simulate = sh_manager.get_shipcalls_for_date(date_to_plan)
        print(get_vessels_schedule(arrivals_sh_to_simulate))

        remaining_slots = LIMIT - total_processed_shipcalls

        if len(arrivals_sh_to_simulate) > remaining_slots:
            arrivals_sh_to_simulate = arrivals_sh_to_simulate[:remaining_slots]

        if not arrivals_sh_to_simulate:
            continue

        total_processed_shipcalls += len(arrivals_sh_to_simulate)

        # Simular arrivals - NOTA: pasamos output_folder como parámetro
        simulate(
            arrivals_sh_to_simulate,
            arrivals_modellogsimul,
            os.getenv('WAITING_ACTIVITY'),
            date_to_plan,
            arrival_or_departure=0,
            output_folder=str(folder_number)
        )
        unfinished_shipcalls.extend(arrivals_sh_to_simulate)

        # Simular departures
        departures_sh_to_simulate = sh_manager.get_departure_shipcalls_for_date(date_to_plan, unfinished_shipcalls)
        departures_modellogsimul = ModelLogSimulation(
            os.getenv('PROCESS_MODEL_DEPARTURES'),
            os.getenv('ACTIVITIES_DURATION_DEPARTURES'),
            os.getenv('ACTIVITIES_RESOURCES_DEPARTURES'),
            os.getenv('ACTIVITIES_GATEWAYS_PERCENTAGES_DEPARTURE')
        )

        simulate(
            departures_sh_to_simulate,
            departures_modellogsimul,
            os.getenv('WAITING_ACTIVITY_DEPARTURE'),
            date_to_plan,
            arrival_or_departure=1,
            output_folder=str(folder_number)
        )

    print(f"✓ Simulación #{folder_number} completada")



if __name__ == '__main__':
    # ===================================================================
    # CONFIGURACIÓN DE INTERVENCIONES DESDE ARCHIVOS CSV
    # ===================================================================

    # Paths a los archivos CSV de configuración
    # Si no existen, se ejecutará sin esas intervenciones específicas
    RESOURCES_CSV = './config/resources_interventions.csv'
    ACTIVITIES_CSV = './config/activities_interventions.csv'
    PERCENTAGES_CSV = './config/percentages_interventions.csv'

    # Fechas de activación de las intervenciones
    # Solo aquí defines las fechas, el resto viene de los CSV
    RESOURCES_INTERVENTION_DATE = date(2021, 1, 4)
    ACTIVITIES_INTERVENTION_DATE = date(2021, 1, 4)
    PERCENTAGES_INTERVENTION_DATE = date(2021, 1, 4)

    # ===================================================================
    # Crear configuración de intervenciones desde archivos CSV
    # Retorna un diccionario en el formato que espera InterventionsFactory
    # ===================================================================

    print("\n" + "="*80)
    print("CARGANDO CONFIGURACIÓN DE INTERVENCIONES DESDE CSV")
    print("="*80)

    interventions_config = create_interventions_from_csv_files(
        resources_csv=RESOURCES_CSV,
        activities_csv=ACTIVITIES_CSV,
        percentages_csv=PERCENTAGES_CSV,
        resources_intervention_date=RESOURCES_INTERVENTION_DATE,
        activities_intervention_date=ACTIVITIES_INTERVENTION_DATE,
        percentages_intervention_date=PERCENTAGES_INTERVENTION_DATE
    )

    # Mostrar resumen de configuración cargada
    print("\nResumen de configuración:")
    print(f"  - Recursos: {len(interventions_config['resource_intervention_info'])} tipo(s)")
    print(f"  - Actividades: {len(interventions_config['activity_intervention_info'])} actividad(es)")
    print(f"  - Gateways: {len(interventions_config['percentage_intervention_info'])} gateway(s)")
    print(f"  - Fecha intervención recursos: {interventions_config['resources_intervention_date']}")
    print(f"  - Fecha intervención actividades: {interventions_config['activities_intervention_date']}")
    print(f"  - Fecha intervención porcentajes: {interventions_config['percentages_intervention_date']}")

    print("\n✓ Configuración cargada correctamente\n")

    # ===================================================================
    # Ejecutar el batch de simulaciones
    # ===================================================================

    # Número de simulaciones a ejecutar
    NUM_SIMULATIONS = 30

    # Ejecutar
    print(f"\n{'#'*80}")
    print(f"INICIO DE BATCH DE SIMULACIONES")
    print(f"Total de simulaciones: {NUM_SIMULATIONS}")
    print(f"{'#'*80}\n")

    # Ejecutar cada simulación
    for i in range(1, NUM_SIMULATIONS + 1):
        try:
            run_single_simulation(i, interventions_config)
        except Exception as e:
            print(f"❌ Error en simulación #{i}: {e}")
            import traceback
            traceback.print_exc()
            continue

    print(f"\n{'#'*80}")
    print(f"BATCH DE SIMULACIONES COMPLETADO")
    print(f"Resultados guardados en: caseStudy/logDinamico/[1-{NUM_SIMULATIONS}]")
    print(f"{'#'*80}\n")

    sys.exit(0)




