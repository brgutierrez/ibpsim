from datetime import datetime
import csv
import simpy
from typing import List

from business_process_simulator_interventions.data.shipcall_info import ShipcallInfo
from business_process_simulator_interventions.data.simulation_model import ModelLogSimulation
from business_process_simulator_interventions.interventions.custom_resource_factory import CustomResourceFactory
from business_process_simulator_interventions.interventions.interventions_management import interventions_launcher
from business_process_simulator_interventions.simulation.trace_runner import trace_runner


def simulate(sh_to_simulate: List[ShipcallInfo], modellogsimul: ModelLogSimulation, waiting_activity: str,
             date_to_plan: str,
             arrival_or_departure: int = 0, output_folder: str = '1') -> None:

    # arrival_or_departure --> 0 = arrivals
    # arrival_or_departure --> 1 = departures

    date_to_plan_dt = datetime.strptime(date_to_plan, '%m/%d/%Y %H:%M:%S')
    result_log_file_path = f'./results/{date_to_plan_dt.strftime("%d_%B_%Y")}-simulated-log.csv'

    if arrival_or_departure == 0:
        with open(result_log_file_path, 'w+', newline='') as f:
            csvwriter = csv.writer(f)
            csvwriter.writerow(['case_id', 'activity', 'time:timestamp:start', 'time:timestamp:end'])

            results_log = []
            env = simpy.Environment()

            modellogsimul.interventions_factory.create_all_interventions(env, modellogsimul, date_to_plan_dt)
            interventions_launcher(modellogsimul.interventions_factory.interventions_to_launch)

            for trace_id in range(len(sh_to_simulate)):
                sh_to_simulate[trace_id].trace_id = trace_id
                sh_to_simulate[trace_id].sh_date = date_to_plan_dt
                sh_to_simulate[trace_id].simulated_log_file_path = result_log_file_path
                env.process(trace_runner(env, trace_id, modellogsimul.resources_object, modellogsimul, waiting_activity,
                                         sh_to_simulate[trace_id], date_to_plan_dt, results_log, arrival_or_departure))

            env.run()

            for row in results_log:
                csvwriter.writerow(row)

    elif arrival_or_departure == 1:
        dict_to_write = {}
        env = simpy.Environment()

        model_resources = {r: CustomResourceFactory.create_custom_resource(env, r, 2) for r in
                           modellogsimul.resources_types}

        for sh in sh_to_simulate:
            results_log = []
            date_to_plan_dt = sh.sh_date
            env.process(trace_runner(env, sh.trace_id, model_resources, modellogsimul, waiting_activity, sh,
                                     date_to_plan_dt, results_log, arrival_or_departure))

            result_log_file_path = sh.simulated_log_file_path
            dict_to_write[result_log_file_path] = results_log

        env.run()

        for filepath, content in dict_to_write.items():
            with open(filepath, 'a+', newline='') as f:
                csvwriter = csv.writer(f)
                for row in content:
                    csvwriter.writerow(row)
