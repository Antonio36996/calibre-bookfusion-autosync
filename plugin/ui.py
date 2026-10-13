__license__ = 'GPL v3'

from qt.core import QIcon, QMenu, QTimer

from calibre.gui2.actions import InterfaceAction

from calibre_plugins.bookfusion_autosync.config import prefs


class AutoSyncAction(InterfaceAction):
    name = 'BookFusion AutoSync'

    action_spec = ('BookFusion AutoSync', None,
                   'Sync a Calibre-Web shelf to BookFusion', None)
    action_type = 'current'

    def genesis(self):
        from calibre_plugins.bookfusion_autosync.runner import AutoSyncRunner
        self.runner = AutoSyncRunner(self.gui)

        self.menu = QMenu(self.gui)
        self.create_menu_action(self.menu, 'bookfusion-autosync-now', 'Sync now',
                                triggered=self.sync_now)
        self.create_menu_action(self.menu, 'bookfusion-autosync-full', 'Resync the whole shelf',
                                description='Also resends metadata of books that were already uploaded',
                                triggered=self.sync_full)
        self.menu.addSeparator()
        self.create_menu_action(self.menu, 'bookfusion-autosync-config', 'Configure...',
                                triggered=self.show_config)

        self.qaction.setMenu(self.menu)
        self.qaction.setIcon(QIcon.ic('sync.png'))
        self.qaction.triggered.connect(self.sync_now)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.sync_periodic)

    def initialization_complete(self):
        self.apply_settings()
        if prefs['enabled']:
            QTimer.singleShot(prefs['startup_delay_seconds'] * 1000, self.sync_periodic)

    def apply_settings(self):
        self.timer.stop()
        if prefs['enabled']:
            self.timer.start(prefs['interval_minutes'] * 60 * 1000)

    def sync_periodic(self):
        if prefs['enabled']:
            self.runner.run()

    def sync_now(self, *args):
        self.runner.run(manual=True)

    def sync_full(self, *args):
        self.runner.run(full=True, manual=True)

    def show_config(self, *args):
        self.interface_action_base_plugin.do_user_config(self.gui)

    def shutting_down(self):
        self.timer.stop()
        self.runner.cancel()
        return True
