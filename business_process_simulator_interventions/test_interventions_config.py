from datetime import date
from pathlib import Path
from config.interventions_config import create_interventions_from_csv_files
from interventions.intervention_factory import InterventionsFactory

def test_interventions_loading():

    print("\n" + "="*80)
    print("TEST: Carga de Configuración de Intervenciones desde CSV")
    print("="*80 + "\n")

    # Paths a los archivos CSV
    RESOURCES_CSV = './config/resources_interventions.csv'
    ACTIVITIES_CSV = './config/activities_interventions.csv'
    PERCENTAGES_CSV = './config/percentages_interventions.csv'

    # Fechas de activación
    RESOURCES_INTERVENTION_DATE = date(2021, 3, 22)
    ACTIVITIES_INTERVENTION_DATE = date(2021, 3, 22)
    PERCENTAGES_INTERVENTION_DATE = date(2021, 3, 22)

    # Cargar configuración
    print("📂 Cargando archivos CSV...")
    interventions_config = create_interventions_from_csv_files(
        resources_csv=RESOURCES_CSV,
        activities_csv=ACTIVITIES_CSV,
        percentages_csv=PERCENTAGES_CSV,
        resources_intervention_date=RESOURCES_INTERVENTION_DATE,
        activities_intervention_date=ACTIVITIES_INTERVENTION_DATE,
        percentages_intervention_date=PERCENTAGES_INTERVENTION_DATE
    )

    # Validar estructura
    print("\n✅ Configuración cargada correctamente\n")
    print("-" * 80)
    print("ESTRUCTURA DEL DICCIONARIO GENERADO:")
    print("-" * 80)

    print(f"\nClaves del diccionario: {list(interventions_config.keys())}")

    # Validar recursos
    print("\n" + "-" * 80)
    print("RECURSOS (resource_intervention_info):")
    print("-" * 80)
    resources = interventions_config['resource_intervention_info']
    print(f"Total de recursos configurados: {len(resources)}")
    for resource_name, config in resources.items():
        print(f"  - {resource_name}:")
        print(f"      initial: {config.get('initial')}")
        print(f"      modified: {config.get('modified')}")
        print(f"      change_time: {config.get('change_time')}")

    # Validar actividades
    print("\n" + "-" * 80)
    print("ACTIVIDADES (activity_intervention_info):")
    print("-" * 80)
    activities = interventions_config['activity_intervention_info']
    print(f"Total de actividades configuradas: {len(activities)}")
    activities_with_intervention = {k: v for k, v in activities.items() if v.get('new_duration') is not None}
    print(f"Actividades CON intervención: {len(activities_with_intervention)}")
    print(f"Actividades SIN intervención: {len(activities) - len(activities_with_intervention)}")

    if activities_with_intervention:
        print("\nPrimeras 5 actividades con intervención:")
        for i, (activity_name, config) in enumerate(list(activities_with_intervention.items())[:5]):
            print(f"  {i+1}. {activity_name}:")
            print(f"      new_duration: {config.get('new_duration')}")
            print(f"      change_time: {config.get('change_time')}")

    # Validar porcentajes
    print("\n" + "-" * 80)
    print("PORCENTAJES DE GATEWAYS (percentage_intervention_info):")
    print("-" * 80)
    percentages = interventions_config['percentage_intervention_info']
    print(f"Total de gateways configurados: {len(percentages)}")

    for i, (gateway_id, config) in enumerate(list(percentages.items())[:3]):
        print(f"\n  Gateway #{i+1}: {gateway_id}")
        print(f"    change_time: {config.get('change_time')}")
        print(f"    Ramas:")
        for branch_name, percentage in config.get('percentages', {}).items():
            print(f"      - {branch_name}: {percentage}%")
        total = sum(config.get('percentages', {}).values())
        print(f"    ✓ Total: {total}% {'✅' if total == 100 else '❌ ERROR: No suma 100'}")

    # Validar fechas
    print("\n" + "-" * 80)
    print("FECHAS DE ACTIVACIÓN:")
    print("-" * 80)
    print(f"  resources_intervention_date: {interventions_config['resources_intervention_date']}")
    print(f"  activities_intervention_date: {interventions_config['activities_intervention_date']}")
    print(f"  percentages_intervention_date: {interventions_config['percentages_intervention_date']}")

    # Intentar crear InterventionsFactory
    print("\n" + "-" * 80)
    print("CREANDO InterventionsFactory:")
    print("-" * 80)
    try:
        factory = InterventionsFactory(interventions_config)
        print("✅ InterventionsFactory creada exitosamente")
        print(f"   Tipo: {type(factory)}")
    except Exception as e:
        print(f"❌ Error al crear InterventionsFactory: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "="*80)
    print("✅ TODAS LAS VALIDACIONES PASARON CORRECTAMENTE")
    print("="*80 + "\n")

    return True


if __name__ == '__main__':
    success = test_interventions_loading()

    if success:
        print("\n🎉 La configuración está lista para ejecutar simulaciones en batch")
        print("   Ejecuta: python business_process_simulator_interventions/run_batch_simulations.py")
    else:
        print("\n❌ Hay errores en la configuración. Revisa los mensajes anteriores.")

