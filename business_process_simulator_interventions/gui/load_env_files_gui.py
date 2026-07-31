import sys
import os
import dotenv
from PyQt6.QtCore import *
from PyQt6.QtGui import QIntValidator
from PyQt6.QtWidgets import *

from business_process_simulator_interventions.interventions.intervention_factory import InterventionsFactory


class FileBrowser(QWidget):
    OpenFile = 0

    def __init__(self, title, env_var, mode=OpenFile):
        QWidget.__init__(self)

        self.env_var = env_var
        initial_value = os.getenv(env_var)
        self.filepath = initial_value
        layout = QHBoxLayout()
        self.setLayout(layout)
        self.browser_mode = mode
        self.filter_name = 'All files (*.*)'
        self.dirpath = QDir.currentPath()

        self.label = QLabel()
        self.label.setText(title)
        layout.addWidget(self.label)

        self.lineEdit = QLineEdit(self)
        self.lineEdit.setText(initial_value)
        self.lineEdit.setEnabled(False)
        layout.addWidget(self.lineEdit)

        self.button = QPushButton('Search')
        self.button.clicked.connect(self.get_file)
        layout.addWidget(self.button)
        layout.addStretch()

    def get_file(self):
        if self.browser_mode == FileBrowser.OpenFile:
            self.filepath = QFileDialog.getOpenFileName(self, caption='Choose File',
                                                        directory=self.dirpath,
                                                        filter=self.filter_name)[0]
            self.lineEdit.setText(self.filepath)

    def get_paths(self):
        return self.filepath


class ResourceModification(QWidget):
    def __init__(self):
        super().__init__()

        layout = QGridLayout()
        self.setLayout(layout)

        self.initial_label = QLabel("Initial:")
        layout.addWidget(self.initial_label, 0, 0)

        self.initial_input = QLineEdit()
        self.initial_input.setValidator(QIntValidator(1, 99))  # Allow numbers between 1 and 99
        self.initial_input.setFixedWidth(50)
        self.initial_input.setText("8")  # Default value set to 1
        layout.addWidget(self.initial_input, 0, 1)

        self.modified_label = QLabel("Modified:")
        layout.addWidget(self.modified_label, 0, 2)

        self.modified_input = QLineEdit()
        self.modified_input.setValidator(QIntValidator(0, 99))  # Allow numbers between 0 and 99
        self.modified_input.setFixedWidth(50)
        layout.addWidget(self.modified_input, 0, 3)

        self.change_time_label = QLabel("Change Time:")
        layout.addWidget(self.change_time_label, 0, 4)

        self.change_time_input = QLineEdit()
        self.change_time_input.setValidator(QIntValidator(0, 9999999))  # Allow any integer
        self.change_time_input.setFixedWidth(50)
        layout.addWidget(self.change_time_input, 0, 5)


class ActivityDurationModification(QWidget):
    def __init__(self, activity_name, initial_duration):
        super().__init__()

        layout = QGridLayout()
        self.setLayout(layout)

        self.activity_label = QLabel(f"{activity_name} (Initial Duration: {initial_duration}):")
        layout.addWidget(self.activity_label, 0, 0, 1, 2)

        self.new_duration_label = QLabel("New Duration:")
        layout.addWidget(self.new_duration_label, 0, 2)

        self.new_duration_input = QLineEdit()
        self.new_duration_input.setValidator(QIntValidator(1, 2147483647))  # Allow any integer > 1
        self.new_duration_input.setFixedWidth(50)
        layout.addWidget(self.new_duration_input, 0, 3)

        self.change_time_label = QLabel("Change Time:")
        layout.addWidget(self.change_time_label, 0, 4)

        self.change_time_input = QLineEdit()
        self.change_time_input.setValidator(QIntValidator(0, 9999999))  # Allow any integer
        self.change_time_input.setFixedWidth(50)
        layout.addWidget(self.change_time_input, 0, 5)


class PercentageIntervention(QWidget):
    def __init__(self, gateway_id, gateway_data, parent=None):
        super(PercentageIntervention, self).__init__(parent)
        self.gateway_id = gateway_id
        self.gateway_data = gateway_data
        self.branch_percentages = {}

        layout = QGridLayout()

        gateway_label = QLabel(f"Gateway ID: {gateway_id}")
        layout.addWidget(gateway_label, 0, 0, 1, 2)

        row = 1
        for branch, percentage in gateway_data.percentages.items():
            branch_label = QLabel(f"{branch}:")
            branch_input = QLineEdit()
            branch_input.setValidator(QIntValidator(1, 99))  # Allow numbers between 1 and 99
            branch_input.setFixedWidth(50)
            branch_input.setText(str(percentage))
            self.branch_percentages[branch] = branch_input

            layout.addWidget(branch_label, row, 0)
            layout.addWidget(branch_input, row, 1)
            row += 1

        # Añadir input de change_time
        change_time_label = QLabel("Change Time:")
        self.change_time_input = QLineEdit()
        self.change_time_input.setValidator(QIntValidator(0, 9999999))  # Allow any integer
        self.change_time_input.setFixedWidth(50)

        layout.addWidget(change_time_label, row, 0)
        layout.addWidget(self.change_time_input, row, 1)

        self.setLayout(layout)


class Demo(QDialog):
    def __init__(self, arrivals_modellogsimul, parent=None):
        QDialog.__init__(self, parent)

        self.activities_intervention_date = None
        self.resources_intervention_date = None
        self.percentages_intervention_date = None

        self.resource_info = {}
        self.activity_info = {}
        self.percentage_info = {}
        self.sync_point_activity = None
        self.modellogsimul_arrivals = arrivals_modellogsimul

        self.setWindowTitle("Initial File Browsing To Configure The Simulator")
        self.resize(600, 800)  # Set initial size

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        vlayout = QVBoxLayout()
        container_widget = QWidget()
        container_widget.setLayout(vlayout)
        scroll_area.setWidget(container_widget)

        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll_area)
        self.setLayout(main_layout)

        self.file_browser_panel(vlayout)
        vlayout.addStretch()
        self.add_sync_point_zone(vlayout)
        self.add_interventions_zone(vlayout)
        self.add_button_panel(vlayout)
        self.show()

    def file_browser_panel(self, parent_layout):
        vlayout = QVBoxLayout()

        self.vessels_data = FileBrowser('Vessels Data', 'VESSELS_DATA', FileBrowser.OpenFile)
        self.process_model = FileBrowser('Process Model', 'PROCESS_MODEL', FileBrowser.OpenFile)
        self.activities_duration = FileBrowser('Activities Duration', 'ACTIVITIES_DURATION', FileBrowser.OpenFile)
        self.process_model_departures = FileBrowser('Process Model Departures', 'PROCESS_MODEL_DEPARTURES',
                                                    FileBrowser.OpenFile)
        self.activities_duration_departures = FileBrowser('Activities Duration Departures',
                                                          'ACTIVITIES_DURATION_DEPARTURES', FileBrowser.OpenFile)
        self.activities_resouces = FileBrowser('Activities Resources', 'ACTIVITIES_RESOURCES', FileBrowser.OpenFile)
        self.activities_resouces_departures = FileBrowser('Activities Resources Departures',
                                                          'ACTIVITIES_RESOURCES_DEPARTURES', FileBrowser.OpenFile)

        self.gateways_percentages = FileBrowser('Gateways Percentages', 'ACTIVITIES_GATEWAYS_PERCENTAGES',
                                                FileBrowser.OpenFile)
        self.gateways_percentages_departures = FileBrowser('Gateways Percentages Departures',
                                                           'ACTIVITIES_GATEWAYS_PERCENTAGES_DEPARTURE',
                                                           FileBrowser.OpenFile)
        self.all_paths = [self.vessels_data, self.process_model, self.activities_duration,
                          self.process_model_departures, self.activities_duration_departures, self.activities_resouces,
                          self.activities_resouces_departures, self.gateways_percentages,
                          self.gateways_percentages_departures]

        vlayout.addWidget(self.vessels_data)
        vlayout.addWidget(self.process_model)
        vlayout.addWidget(self.activities_duration)
        vlayout.addWidget(self.process_model_departures)
        vlayout.addWidget(self.activities_duration_departures)
        vlayout.addWidget(self.activities_resouces)
        vlayout.addWidget(self.activities_resouces_departures)
        vlayout.addWidget(self.gateways_percentages)
        vlayout.addWidget(self.gateways_percentages_departures)

        vlayout.addStretch()
        parent_layout.addLayout(vlayout)

    def add_sync_point_zone(self, parent_layout):
        hline = QFrame()
        hline.setFrameShape(QFrame.Shape.HLine)
        hline.setFrameShadow(QFrame.Shadow.Sunken)
        parent_layout.addWidget(hline)

        sync_label = QLabel("Synchronisation points")
        sync_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        parent_layout.addWidget(sync_label)

        description_label = QLabel("Select an activity for the synchronisation point:")
        parent_layout.addWidget(description_label)

        self.sync_point_combo = QComboBox()
        self.sync_point_combo.addItems(self.modellogsimul_arrivals.activities)
        self.sync_point_combo.setCurrentText(os.getenv('WAITING_ACTIVITY', ''))
        parent_layout.addWidget(self.sync_point_combo)

        hline2 = QFrame()
        hline2.setFrameShape(QFrame.Shape.HLine)
        hline2.setFrameShadow(QFrame.Shadow.Sunken)
        parent_layout.addWidget(hline2)

    def add_interventions_zone(self, parent_layout: QVBoxLayout):
        hline = QFrame()
        hline.setFrameShape(QFrame.Shape.HLine)
        hline.setFrameShadow(QFrame.Shadow.Sunken)
        parent_layout.addWidget(hline)

        interventions_label = QLabel("Interventions")
        interventions_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        parent_layout.addWidget(interventions_label)

        hline2 = QFrame()
        hline2.setFrameShape(QFrame.Shape.HLine)
        hline.setFrameShadow(QFrame.Shadow.Sunken)
        parent_layout.addWidget(hline2)

        self.add_resource_intervention(parent_layout)
        self.add_activity_duration_intervention(parent_layout)
        self.add_percentage_intervention(parent_layout)

        hline3 = QFrame()
        hline3.setFrameShape(QFrame.Shape.HLine)
        hline3.setFrameShadow(QFrame.Shadow.Sunken)
        parent_layout.addWidget(hline3)

    def add_resource_intervention(self, parent_layout: QVBoxLayout):
        interventions_label = QLabel("Number of resources intervention: ")
        interventions_label.setStyleSheet("font-weight: bold;")
        parent_layout.addWidget(interventions_label)

        date_layout = QHBoxLayout()
        intervention_date_label = QLabel("Intervention Date:")
        intervention_date_label.setFixedWidth(150)
        date_layout.addWidget(intervention_date_label)

        # Crear un widget de selección de fecha
        self.resources_intervention_date = QDateEdit()
        self.resources_intervention_date.setCalendarPopup(True)
        self.resources_intervention_date.setMinimumDate(QDate(2021, 1, 1))
        self.resources_intervention_date.setMaximumDate(QDate(2021, 12, 31))
        self.resources_intervention_date.setDate(QDate(2021, 3, 22))  # Fecha inicial predeterminada
        date_layout.addWidget(self.resources_intervention_date)

        parent_layout.addLayout(date_layout)

        description_label = QLabel("Provide the number of resources available for each type:")
        parent_layout.addWidget(description_label)

        self.resource_info = dict()

        for resource in self.modellogsimul_arrivals.resources_types:
            resource_layout = QGridLayout()

            resource_label = QLabel(f"{resource}:")
            resource_layout.addWidget(resource_label, 0, 0)

            modification_widget = ResourceModification()
            resource_layout.addWidget(modification_widget, 1, 0, 1, 6)

            parent_layout.addLayout(resource_layout)

            self.resource_info[resource] = modification_widget

    def add_activity_duration_intervention(self, parent_layout: QVBoxLayout):
        interventions_label = QLabel("Activity duration intervention: ")
        interventions_label.setStyleSheet("font-weight: bold;")
        parent_layout.addWidget(interventions_label)

        description_label = QLabel("Provide the new duration and change time for each activity:")
        parent_layout.addWidget(description_label)

        # Agregar el campo de fecha para Activity Duration Intervention
        date_layout = QHBoxLayout()
        intervention_date_label = QLabel("Intervention Date:")
        intervention_date_label.setFixedWidth(150)
        date_layout.addWidget(intervention_date_label)

        self.activities_intervention_date = QDateEdit()
        self.activities_intervention_date.setCalendarPopup(True)
        self.activities_intervention_date.setMinimumDate(QDate(2021, 1, 1))
        self.activities_intervention_date.setMaximumDate(QDate(2021, 12, 31))
        self.activities_intervention_date.setDate(QDate(2021, 3, 22))  # Fecha inicial predeterminada
        date_layout.addWidget(self.activities_intervention_date)

        parent_layout.addLayout(date_layout)
        self.activity_info = dict()

        for activity, duration in self.modellogsimul_arrivals.activities_duration.items():
            activity_layout = QGridLayout()

            modification_widget = ActivityDurationModification(activity, duration)
            activity_layout.addWidget(modification_widget, 0, 0, 1, 6)

            parent_layout.addLayout(activity_layout)

            self.activity_info[activity] = modification_widget

    def add_percentage_intervention(self, parent_layout):
        interventions_label = QLabel("Percentage Intervention: ")
        interventions_label.setStyleSheet("font-weight: bold;")
        parent_layout.addWidget(interventions_label)

        description_label = QLabel("Modify the percentage and change time associated with each branch of the gateways:")
        parent_layout.addWidget(description_label)

        # Añadir widget de fecha para la intervención de porcentajes
        date_layout = QHBoxLayout()
        intervention_date_label = QLabel("Intervention Date:")
        intervention_date_label.setFixedWidth(150)
        date_layout.addWidget(intervention_date_label)

        # Crear un widget de selección de fecha para percentages_intervention_date
        self.percentages_intervention_date = QDateEdit()
        self.percentages_intervention_date.setCalendarPopup(True)
        self.percentages_intervention_date.setMinimumDate(QDate(2021, 1, 1))
        self.percentages_intervention_date.setMaximumDate(QDate(2021, 12, 31))
        self.percentages_intervention_date.setDate(QDate(2021, 3, 22))  # Fecha inicial predeterminada
        date_layout.addWidget(self.percentages_intervention_date)

        parent_layout.addLayout(date_layout)

        self.percentage_info = {}

        for gateway_id, gateway_data in self.modellogsimul_arrivals.activities_percentages.items():
            gateway_layout = QVBoxLayout()

            gateway_label = QLabel(f"Gateway {gateway_id}:")
            gateway_layout.addWidget(gateway_label)

            percentage_intervention = PercentageIntervention(gateway_id, gateway_data)
            gateway_layout.addWidget(percentage_intervention)

            self.percentage_info[gateway_id] = percentage_intervention

            parent_layout.addLayout(gateway_layout)

        hline = QFrame()
        hline.setFrameShape(QFrame.Shape.HLine)
        hline.setFrameShadow(QFrame.Shadow.Sunken)
        parent_layout.addWidget(hline)

    def add_button_panel(self, parent_layout):
        hlayout = QHBoxLayout()
        hlayout.addStretch()

        self.button = QPushButton("OK")
        self.button.clicked.connect(self.button_action)
        hlayout.addWidget(self.button)
        parent_layout.addLayout(hlayout)

    def button_action(self):
        # Variables para almacenar los datos de los recursos, actividades y porcentajes de gateways
        resource_data = {}
        activity_data = {}
        percentage_data = {}

        # Bandera para seguir o no con el cierre de la ventana
        valid = True

        for var_path in self.all_paths:
            update_env_var(var_path.env_var, var_path.get_paths())

        selected_activity = self.sync_point_combo.currentText()
        update_env_var('WAITING_ACTIVITY', selected_activity)

        # Validaciones de recursos
        for resource, widget in self.resource_info.items():
            initial_count = widget.initial_input.text()
            modified_count = widget.modified_input.text()
            change_time = widget.change_time_input.text()

            # Validar conteo inicial
            if not (initial_count.isdigit() and 1 <= int(initial_count) <= 99):
                valid = False
                QMessageBox.warning(self, "Invalid Input",
                                    f"Please enter a valid initial number for {resource} (1-99).")
                return

            # Validar conteo modificado y tiempo de cambio
            modified_count = int(modified_count) if modified_count.isdigit() else None
            change_time = int(change_time) if change_time.isdigit() else None

            if (modified_count is None or modified_count == 0) and (change_time is not None and change_time > 0):
                valid = False
                QMessageBox.warning(self, "Invalid Input",
                                    f"Change time must be 0 or empty if modified count is 0 or empty for {resource}.")
                return

            if (modified_count is not None and modified_count > 0) and (change_time is None or change_time == 0):
                valid = False
                QMessageBox.warning(self, "Invalid Input",
                                    f"Modified count must be 0 or empty if change time is 0 or empty for {resource}.")
                return

            resource_data[resource] = {
                'initial': int(initial_count),
                'modified': modified_count if modified_count != 0 else None,
                'change_time': change_time if change_time != 0 else None
            }

        # Validaciones de actividades
        for activity, widget in self.activity_info.items():
            new_duration = widget.new_duration_input.text()
            change_time = widget.change_time_input.text()

            # Validar nueva duración
            if new_duration:
                if not (new_duration.isdigit() and int(new_duration) > 1):
                    valid = False
                    QMessageBox.warning(self, "Invalid Input",
                                        f"Please enter a valid new duration for {activity} (must be > 1).")
                    return

                # Validar tiempo de cambio
                change_time = int(change_time) if change_time.isdigit() else None
                if change_time is None or not (0 <= change_time <= 9999999):
                    valid = False
                    QMessageBox.warning(self, "Invalid Input",
                                        f"Please enter a valid change time for {activity} (0-9999999).")
                    return

                activity_data[activity] = {
                    'new_duration': int(new_duration),
                    'change_time': change_time
                }
            else:
                if change_time:
                    valid = False
                    QMessageBox.warning(self, "Invalid Input",
                                        f"Cannot provide change time without specifying a new duration for {activity}.")
                    return

                activity_data[activity] = {
                    'new_duration': None,
                    'change_time': None
                }

        # Validaciones de porcentajes de gateways
        for gateway_id, percentage_intervention in self.percentage_info.items():
            total_percentage = 0
            gateway_data = {}
            for branch, percentage_input in percentage_intervention.branch_percentages.items():
                percentage_text = percentage_input.text().strip()

                if not percentage_text:
                    valid = False
                    QMessageBox.warning(self, "Invalid Input",
                                        f"Please enter a percentage for branch {branch} of gateway {gateway_id}.")
                    return

                percentage = int(percentage_text)

                if percentage < 0:
                    valid = False
                    QMessageBox.warning(self, "Invalid Input",
                                        f"The percentage for branch {branch} of gateway {gateway_id} must be at least 0.")
                    return

                if percentage > 99:
                    valid = False
                    QMessageBox.warning(self, "Invalid Input",
                                        f"The percentage for branch {branch} of gateway {gateway_id} cannot exceed 99.")
                    return

                total_percentage += percentage
                gateway_data[branch] = percentage

            if total_percentage != 100:
                valid = False
                QMessageBox.warning(self, "Invalid Input",
                                    f"The sum of percentages for gateway {gateway_id} must be equal to 100.")
                return

            change_time_text = percentage_intervention.change_time_input.text().strip()
            change_time = int(change_time_text) if change_time_text.isdigit() else None

            percentage_data[gateway_id] = {
                'percentages': gateway_data,
                'change_time': change_time
            }

        # Solo si todas las validaciones son exitosas, actualizamos los datos y cerramos la ventana
        if valid:
            self.resource_info.update(resource_data)
            self.activity_info.update(activity_data)
            self.percentage_info.update(percentage_data)
            # print("Resource Info:", self.resource_info)  # Imprimir datos de recursos actualizados
            # print("Activity Info:", self.activity_info)  # Imprimir datos de actividades actualizados
            # print("Percentage Info:", self.percentage_info)  # Imprimir datos de porcentajes actualizados

            self.close()


def update_env_var(var_name, new_value):
    old_value = os.getenv(var_name)
    if not new_value is None and new_value != old_value:
        os.environ[var_name] = new_value
        # Write changes to .env.example file.
        dotenv.set_key(dotenv.find_dotenv(), var_name, os.environ[var_name])


def get_gui(arrivals_modellogsimul):
    app = QApplication(sys.argv)
    demo = Demo(arrivals_modellogsimul)
    # demo.show()
    # app.exec()
    demo.exec()
    collected_data = {'resource_intervention_info': demo.resource_info,
                      'activity_intervention_info': demo.activity_info,
                      'percentage_intervention_info': demo.percentage_info,
                      'resources_intervention_date': demo.resources_intervention_date.date().toPyDate(),
                      'activities_intervention_date': demo.activities_intervention_date.date().toPyDate(),
                      'percentages_intervention_date': demo.percentages_intervention_date.date().toPyDate()}

    arrivals_modellogsimul.interventions_factory = InterventionsFactory(collected_data)
    return app
