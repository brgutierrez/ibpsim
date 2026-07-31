import sys
import os
import dotenv
from PyQt6.QtCore import *
from PyQt6.QtWidgets import *


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
        # self.dirpath = QDir.homePath()

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


class Demo(QDialog):
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)

        self.setWindowTitle("Initial File Browsing To Configure The Simulator")

        vlayout = QVBoxLayout()
        self.setLayout(vlayout)

        self.file_browser_panel(vlayout)
        vlayout.addStretch()
        self.add_button_panel(vlayout)
        self.show()

    def file_browser_panel(self, parent_layout):
        vlayout = QVBoxLayout()

        self.vessels_data = FileBrowser('Vessels Data', 'VESSELS_DATA', FileBrowser.OpenFile)
        self.process_model = FileBrowser('Process Model', 'PROCESS_MODEL', FileBrowser.OpenFile)
        self.activities_duration = FileBrowser('Activities Duration', 'ACTIVITIES_DURATION',
                                               FileBrowser.OpenFile)
        self.process_model_departures = FileBrowser('Process Model Departures', 'PROCESS_MODEL_DEPARTURES',
                                                    FileBrowser.OpenFile)
        self.activities_duration_departures = FileBrowser('Activities Duration Departures',
                                                          'ACTIVITIES_DURATION_DEPARTURES',
                                                          FileBrowser.OpenFile)

        self.all_paths = [self.vessels_data, self.process_model, self.activities_duration,
                          self.process_model_departures, self.activities_duration_departures]

        vlayout.addWidget(self.vessels_data)
        vlayout.addWidget(self.process_model)
        vlayout.addWidget(self.activities_duration)
        vlayout.addWidget(self.process_model_departures)
        vlayout.addWidget(self.activities_duration_departures)

        vlayout.addStretch()
        parent_layout.addLayout(vlayout)

    def add_button_panel(self, parent_layout):
        hlayout = QHBoxLayout()
        hlayout.addStretch()

        self.button = QPushButton("OK")
        self.button.clicked.connect(self.button_action)
        hlayout.addWidget(self.button)
        parent_layout.addLayout(hlayout)

    def button_action(self):
        for var_path in self.all_paths:
            update_env_var(var_path.env_var, var_path.get_paths())

        self.close()


def update_env_var(var_name, new_value):
    old_value = os.getenv(var_name)
    if not new_value is None and new_value != old_value:
        os.environ[var_name] = new_value
        # Write changes to .env.example file.
        dotenv.set_key(dotenv.find_dotenv(), var_name, os.environ[var_name])


def get_gui():
    app = QApplication(sys.argv)
    demo = Demo()
    demo.show()
    app.exec()
    return app



# if __name__ == '__main__':
#     app = QApplication(sys.argv)
#     demo = Demo()
#     demo.show()
#     sys.exit(app.exec())
