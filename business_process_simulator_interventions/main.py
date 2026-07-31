import os
import random
import sys
import time

from dotenv import load_dotenv

from business_process_simulator_interventions.data.data_reader import ShipcallManager
from business_process_simulator_interventions.data.simulation_model import ModelLogSimulation
from business_process_simulator_interventions.gui.load_env_files_gui import get_gui
from business_process_simulator_interventions.interventions.external_agent.planner import get_vessels_schedule
from business_process_simulator_interventions.simulation.simulation import simulate

load_dotenv()

random.seed(time.time())

if __name__ == '__main__':
    arrivals_modellogsimul = ModelLogSimulation(os.getenv('PROCESS_MODEL'), os.getenv('ACTIVITIES_DURATION'),
                                                os.getenv('ACTIVITIES_RESOURCES'),
                                                os.getenv('ACTIVITIES_GATEWAYS_PERCENTAGES'))

    gui_app = get_gui(arrivals_modellogsimul)

    #date_to_plan = '06/17/2021 00:00:00'
    #dates_to_simulate = [date_to_plan]

    unfinished_shipcalls = []

    sh_manager = ShipcallManager()
    dates_to_simulate = sh_manager.get_all_shipcalls_dates()
    dates_to_simulate = [d.strftime('%m/%d/%Y %H:%M:%S') for d in dates_to_simulate]

    LIMIT = 20
    total_processed_shipcalls = 0

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

        simulate(arrivals_sh_to_simulate, arrivals_modellogsimul, os.getenv('WAITING_ACTIVITY'), date_to_plan,
                 arrival_or_departure=0, output_folder='1')
        unfinished_shipcalls.extend(arrivals_sh_to_simulate)

        departures_sh_to_simulate = sh_manager.get_departure_shipcalls_for_date(date_to_plan, unfinished_shipcalls)
        departures_modellogsimul = ModelLogSimulation(os.getenv('PROCESS_MODEL_DEPARTURES'),
                                                      os.getenv('ACTIVITIES_DURATION_DEPARTURES'),
                                                      os.getenv('ACTIVITIES_RESOURCES_DEPARTURES'),
                                                      os.getenv('ACTIVITIES_GATEWAYS_PERCENTAGES_DEPARTURE'))

        simulate(departures_sh_to_simulate, departures_modellogsimul, os.getenv('WAITING_ACTIVITY_DEPARTURE'),
                 date_to_plan,
                 arrival_or_departure=1, output_folder='1')

    sys.exit()
