import random
from datetime import datetime

from business_process_simulator_interventions.data.data_reader_aux import get_df_shipcalls
from business_process_simulator_interventions.data.shipcall_info import ShipcallInfo


class ShipcallManager:
    def __init__(self):
        self.__df_shipcalls = get_df_shipcalls()

    def get_shipcalls_for_date(self, shipcalls_date):
        velssels_data = self.__df_shipcalls.loc[self.__df_shipcalls['FECHA_ETA'] == shipcalls_date]
        sh_to_plan = []
        for index, row in velssels_data.iterrows():
            sh = ShipcallInfo(*row)
            sh_to_plan.append(sh)
            # TODO: Como no tengo acceso al planificador, meto un valor aleatorio para dar un nuevo momento de entrada
            sh.new_planner_entry_time = random.randint(30, 90)
            sh.new_planner_departure_time = random.randint(30, 90)
        return sh_to_plan

    def get_all_shipcalls_dates(self):
        return sorted(set(list(self.__df_shipcalls['FECHA_ETA'])))

    @staticmethod
    def get_departure_shipcalls_for_date(date_to_plan, unfinished_shipcalls):
        date_to_plan = datetime.strptime(date_to_plan, '%m/%d/%Y %H:%M:%S')
        sh_to_plan = []
        for sh in unfinished_shipcalls:
            if sh.departure_date.date() == date_to_plan.date():
                sh_to_plan.append(sh)
        return sh_to_plan
