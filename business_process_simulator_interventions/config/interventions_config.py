"""
Configuración programática de intervenciones sin GUI.
Permite definir intervenciones mediante código o archivos CSV para ejecuciones batch.
"""

import pandas as pd
from datetime import date
from pathlib import Path
from business_process_simulator_interventions.interventions.intervention_factory import InterventionsFactory


def create_interventions_config(
    resource_interventions=None,
    activity_interventions=None,
    percentage_interventions=None,
    resources_intervention_date=None,
    activities_intervention_date=None,
    percentages_intervention_date=None
):
    """
    Crea una configuración de intervenciones programáticamente.

    Args:
        resource_interventions: Dict con formato:
            {
                'resource_name': {
                    'initial': int,
                    'modified': int or None,
                    'change_time': int or None
                }
            }

        activity_interventions: Dict con formato:
            {
                'activity_name': {
                    'new_duration': int or None,
                    'change_time': int or None
                }
            }

        percentage_interventions: Dict con formato:
            {
                'gateway_id': {
                    'percentages': {'branch_name': int},
                    'change_time': int or None
                }
            }

        resources_intervention_date: date object
        activities_intervention_date: date object
        percentages_intervention_date: date object

    Returns:
        InterventionsFactory configurada
    """

    # Valores por defecto
    if resource_interventions is None:
        resource_interventions = {}

    if activity_interventions is None:
        activity_interventions = {}

    if percentage_interventions is None:
        percentage_interventions = {}

    # Fechas por defecto (22 de marzo de 2021)
    default_date = date(2021, 3, 22)

    if resources_intervention_date is None:
        resources_intervention_date = default_date

    if activities_intervention_date is None:
        activities_intervention_date = default_date

    if percentages_intervention_date is None:
        percentages_intervention_date = default_date

    # Crear el diccionario de configuración
    collected_data = {
        'resource_intervention_info': resource_interventions,
        'activity_intervention_info': activity_interventions,
        'percentage_intervention_info': percentage_interventions,
        'resources_intervention_date': resources_intervention_date,
        'activities_intervention_date': activities_intervention_date,
        'percentages_intervention_date': percentages_intervention_date
    }

    return InterventionsFactory(collected_data)


def create_no_interventions_config():
    """
    Crea una configuración sin intervenciones (escenario base).

    Returns:
        InterventionsFactory sin intervenciones activas
    """
    return create_interventions_config()


def load_resource_interventions_from_csv(csv_path):
    """
    Lee las intervenciones de recursos desde un archivo CSV.

    Formato esperado del CSV:
        resource_name,initial,modified,change_time
        Practico,8,10,100
        Remolcador,4,,

    Args:
        csv_path: Path al archivo CSV

    Returns:
        Dict con las intervenciones de recursos
    """
    if not Path(csv_path).exists():
        print(f"⚠️  Advertencia: No se encontró el archivo {csv_path}")
        return {}

    df = pd.read_csv(csv_path)
    resource_interventions = {}

    for _, row in df.iterrows():
        resource_name = row['resource_name']
        initial = int(row['initial']) if pd.notna(row['initial']) else None
        modified = int(row['modified']) if pd.notna(row['modified']) else None
        change_time = int(row['change_time']) if pd.notna(row['change_time']) else None

        resource_interventions[resource_name] = {
            'initial': initial,
            'modified': modified,
            'change_time': change_time
        }

    return resource_interventions


def load_activity_interventions_from_csv(csv_path):
    """
    Lee las intervenciones de actividades desde un archivo CSV.

    Formato esperado del CSV:
        activity_name,new_duration,change_time
        Espera para entrar en Canal Principal,50,100
        Inspección,,

    Args:
        csv_path: Path al archivo CSV

    Returns:
        Dict con las intervenciones de actividades
    """
    if not Path(csv_path).exists():
        print(f"⚠️  Advertencia: No se encontró el archivo {csv_path}")
        return {}

    df = pd.read_csv(csv_path)
    activity_interventions = {}

    for _, row in df.iterrows():
        activity_name = row['activity_name']
        new_duration = int(row['new_duration']) if pd.notna(row['new_duration']) else None
        change_time = int(row['change_time']) if pd.notna(row['change_time']) else None

        activity_interventions[activity_name] = {
            'new_duration': new_duration,
            'change_time': change_time
        }

    return activity_interventions


def load_percentage_interventions_from_csv(csv_path):
    """
    Lee las intervenciones de porcentajes de gateways desde un archivo CSV.

    Formato esperado del CSV:
        gateway_id,branch_name,percentage,change_time
        exi_Gateway_1dw5ux8,Espera de asignación de practico,30,100
        exi_Gateway_1dw5ux8,Navegación con práctico asignado,70,100

    Nota: El change_time debe ser el mismo para todas las ramas del mismo gateway.
          Solo se tomará el valor de la primera fila de cada gateway.

    Args:
        csv_path: Path al archivo CSV

    Returns:
        Dict con las intervenciones de porcentajes
    """
    if not Path(csv_path).exists():
        print(f"⚠️  Advertencia: No se encontró el archivo {csv_path}")
        return {}

    df = pd.read_csv(csv_path)
    percentage_interventions = {}

    # Agrupar por gateway_id
    for gateway_id, group in df.groupby('gateway_id'):
        percentages = {}
        change_time = None

        for _, row in group.iterrows():
            branch_name = row['branch_name']
            percentage = int(row['percentage']) if pd.notna(row['percentage']) else 0
            percentages[branch_name] = percentage

            # Tomar el change_time de la primera fila
            if change_time is None and pd.notna(row['change_time']):
                change_time = int(row['change_time'])

        percentage_interventions["exi_"+ gateway_id] = {
            'percentages': percentages,
            'change_time': change_time
        }

    return percentage_interventions


def create_interventions_from_csv_files(
    resources_csv=None,
    activities_csv=None,
    percentages_csv=None,
    resources_intervention_date=None,
    activities_intervention_date=None,
    percentages_intervention_date=None
):
    """
    Crea una configuración de intervenciones leyendo desde archivos CSV.

    Args:
        resources_csv: Path al CSV de intervenciones de recursos
        activities_csv: Path al CSV de intervenciones de actividades
        percentages_csv: Path al CSV de intervenciones de porcentajes
        resources_intervention_date: date object
        activities_intervention_date: date object
        percentages_intervention_date: date object

    Returns:
        Dict con el formato esperado por InterventionsFactory (collected_data)
    """
    resource_interventions = {}
    activity_interventions = {}
    percentage_interventions = {}

    if resources_csv:
        resource_interventions = load_resource_interventions_from_csv(resources_csv)

    if activities_csv:
        activity_interventions = load_activity_interventions_from_csv(activities_csv)

    if percentages_csv:
        percentage_interventions = load_percentage_interventions_from_csv(percentages_csv)

    # Fechas por defecto (22 de marzo de 2021)
    default_date = date(2021, 3, 22)

    if resources_intervention_date is None:
        resources_intervention_date = default_date

    if activities_intervention_date is None:
        activities_intervention_date = default_date

    if percentages_intervention_date is None:
        percentages_intervention_date = default_date

    # Retornar el diccionario en el formato que espera InterventionsFactory
    # Este es el mismo formato que genera la GUI en load_env_files_gui.py
    collected_data = {
        'resource_intervention_info': resource_interventions,
        'activity_intervention_info': activity_interventions,
        'percentage_intervention_info': percentage_interventions,
        'resources_intervention_date': resources_intervention_date,
        'activities_intervention_date': activities_intervention_date,
        'percentages_intervention_date': percentages_intervention_date
    }

    return collected_data
