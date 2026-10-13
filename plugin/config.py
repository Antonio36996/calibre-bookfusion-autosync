__license__ = 'GPL v3'

from qt.core import QWidget, QVBoxLayout, QFormLayout, QLabel, QLineEdit, QSpinBox, QCheckBox
from calibre.utils.config import JSONConfig

prefs = JSONConfig('plugins/bookfusion_autosync')

prefs.defaults['enabled'] = True
prefs.defaults['app_db_path'] = r'C:\Program Files\Calibre-Web\app.db'
prefs.defaults['shelf_name'] = 'BookFusion'
prefs.defaults['interval_minutes'] = 5
prefs.defaults['startup_delay_seconds'] = 60


class ConfigWidget(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.l = QVBoxLayout()
        self.setLayout(self.l)

        self.l.addWidget(QLabel(
            'Books on the selected Calibre-Web shelf are sent to BookFusion\n'
            'using the API key and settings of the official BookFusion plugin.'
        ))

        self.form = QFormLayout()
        self.form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.l.addLayout(self.form)

        self.enabled = QCheckBox('Sync periodically', self)
        self.enabled.setChecked(prefs['enabled'])
        self.form.addRow('Enabled:', self.enabled)

        self.app_db_path = QLineEdit(prefs['app_db_path'], self)
        self.form.addRow('Calibre-Web app.db:', self.app_db_path)

        self.shelf_name = QLineEdit(prefs['shelf_name'], self)
        self.form.addRow('Shelf:', self.shelf_name)

        self.interval_minutes = QSpinBox(self)
        self.interval_minutes.setRange(1, 1440)
        self.interval_minutes.setSuffix(' min')
        self.interval_minutes.setValue(prefs['interval_minutes'])
        self.form.addRow('Interval:', self.interval_minutes)

        self.startup_delay_seconds = QSpinBox(self)
        self.startup_delay_seconds.setRange(5, 3600)
        self.startup_delay_seconds.setSuffix(' s')
        self.startup_delay_seconds.setValue(prefs['startup_delay_seconds'])
        self.form.addRow('Startup delay:', self.startup_delay_seconds)

    def save_settings(self):
        prefs['enabled'] = self.enabled.isChecked()
        prefs['app_db_path'] = self.app_db_path.text().strip()
        prefs['shelf_name'] = self.shelf_name.text().strip()
        prefs['interval_minutes'] = self.interval_minutes.value()
        prefs['startup_delay_seconds'] = self.startup_delay_seconds.value()
