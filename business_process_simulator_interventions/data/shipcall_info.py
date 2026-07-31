from datetime import datetime


class ShipcallInfo:
    def __init__(self, id_shipcall, vessel_name, vessel_imo, eta_date, eta_time, vessel_length, beam, vessel_vel_max,
                 draught, etd_date, etd_time):
        self.__id_shipcall = id_shipcall
        self.__vessel_name = vessel_name
        self.__vessel_imo = vessel_imo
        self.__eta_date = eta_date
        self.__eta_time = eta_time
        self.__vessel_length = float(vessel_length)
        self.__beam = float(beam)
        self.__vel_max = float(vessel_vel_max) if vessel_vel_max and float(vessel_vel_max) > 0 else 20
        self.__draught = self.__compute_draught(float(draught)) if draught and float(draught) > 0 else 6.5
        self.__eta = self.__compute_timestamps(eta_date, eta_time)
        self.__vessel_size = self.__compute_vessel_size(self.vessel_length)
        self.__new_planner_entry_time = None
        self.__new_planner_departure_time = None
        self.__etd_date = etd_date
        self.__etd_time = etd_time
        self.__etd = self.__compute_timestamps(etd_date, etd_time)
        self.__sh_date = None
        self.__last_timestamp_recorded = None
        self.__trace_id = None
        self.__departure_date = None
        self.__simulated_log_file_path = None

    @staticmethod
    def __compute_timestamps(new_date, new_time):
        date = new_date if isinstance(new_date, datetime) else datetime.strptime(new_date, '%Y-%m-%d')
        time = new_time if isinstance(new_time, datetime) else datetime.strptime(new_time, '%H:%M:%S')
        return datetime.combine(date.date(), time.time())

    @staticmethod
    def __compute_vessel_size(vessel_length):
        if vessel_length < 90:
            return 1
        elif vessel_length < 140:
            return 2
        elif vessel_length < 180:
            return 4
        return vessel_length

    @staticmethod
    def __compute_draught(dr_value):
        numb_int_str = str(int(dr_value))
        numb_len = len(numb_int_str)
        if numb_len == 4:
            return dr_value / 1000
        elif numb_len == 3:
            return dr_value / 100
        elif numb_len == 2:
            return dr_value / 10
        return dr_value

    def __str__(self):
        return (f'ShipcallInfo(id_shipcall={self.id_shipcall}, vessel_name={self.vessel_name}, '
                f'vessel_imo={self.vessel_imo}, eta_date={self.eta_date}, eta_time={self.eta_time}, '
                f'vessel_length={self.vessel_length}, beam={self.beam}, vel_max={self.vel_max}, '
                f'draught={self.draught}, eta={self.eta}, vessel_size={self.vessel_size}, '
                f'etd={self.etd}, new_planner_entry_time={self.new_planner_entry_time})')

    @property
    def id_shipcall(self):
        return self.__id_shipcall

    @id_shipcall.setter
    def id_shipcall(self, value):
        self.__id_shipcall = value

    @property
    def vessel_name(self):
        return self.__vessel_name

    @vessel_name.setter
    def vessel_name(self, value):
        self.__vessel_name = value

    @property
    def vessel_imo(self):
        return self.__vessel_imo

    @vessel_imo.setter
    def vessel_imo(self, value):
        self.__vessel_imo = value

    @property
    def eta_date(self):
        return self.__eta_date

    @eta_date.setter
    def eta_date(self, value):
        self.__eta_date = value

    @property
    def eta_time(self):
        return self.__eta_time

    @eta_time.setter
    def eta_time(self, value):
        self.__eta_time = value

    @property
    def vessel_length(self):
        return self.__vessel_length

    @vessel_length.setter
    def vessel_length(self, value):
        self.__vessel_length = float(value)

    @property
    def beam(self):
        return self.__beam

    @beam.setter
    def beam(self, value):
        self.__beam = float(value)

    @property
    def vel_max(self):
        return self.__vel_max

    @vel_max.setter
    def vel_max(self, value):
        self.__vel_max = float(value) if value and float(value) > 0 else 20

    @property
    def draught(self):
        return self.__draught

    @draught.setter
    def draught(self, value):
        self.__draught = self.__compute_draught(float(value)) if value and float(value) > 0 else 6.5

    @property
    def eta(self):
        return self.__eta

    @property
    def vessel_size(self):
        return self.__vessel_size

    @property
    def new_planner_entry_time(self):
        return self.__new_planner_entry_time

    @new_planner_entry_time.setter
    def new_planner_entry_time(self, value):
        self.__new_planner_entry_time = value

    @property
    def new_planner_departure_time(self):
        return self.__new_planner_departure_time

    @new_planner_departure_time.setter
    def new_planner_departure_time(self, value):
        self.__new_planner_departure_time = value

    @property
    def etd_date(self):
        return self.__etd_date

    @etd_date.setter
    def etd_date(self, value):
        self.__etd_date = value

    @property
    def etd_time(self):
        return self.__etd_time

    @etd_time.setter
    def etd_time(self, value):
        self.__etd_time = value

    @property
    def etd(self):
        return self.__etd

    @property
    def sh_date(self):
        return self.__sh_date

    @sh_date.setter
    def sh_date(self, value):
        self.__sh_date = value

    @property
    def last_timestamp_recorded(self):
        return self.__last_timestamp_recorded

    @last_timestamp_recorded.setter
    def last_timestamp_recorded(self, value):
        self.__last_timestamp_recorded = value
        self.__departure_date = value if value > self.__etd else self.__etd

    @property
    def trace_id(self):
        return self.__trace_id

    @trace_id.setter
    def trace_id(self, value):
        self.__trace_id = value

    @property
    def departure_date(self):
        return self.__departure_date

    @departure_date.setter
    def departure_date(self, value):
        self.__departure_date = value

    @property
    def simulated_log_file_path(self):
        return self.__simulated_log_file_path

    @simulated_log_file_path.setter
    def simulated_log_file_path(self, value):
        self.__simulated_log_file_path = value
