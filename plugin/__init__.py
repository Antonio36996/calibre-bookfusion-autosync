__license__ = 'GPL v3'

from calibre.customize import InterfaceActionBase


class BookFusionAutoSyncPlugin(InterfaceActionBase):
    name = 'BookFusion AutoSync'
    description = ('Automatically syncs the books on a Calibre-Web shelf to BookFusion, '
                   'reusing the official BookFusion plugin.')
    supported_platforms = ['windows', 'osx', 'linux']
    author = 'Antonio36996'
    version = (0, 1, 0)
    minimum_calibre_version = (6, 2, 1)

    actual_plugin = 'calibre_plugins.bookfusion_autosync.ui:AutoSyncAction'

    def is_customizable(self):
        return True

    def config_widget(self):
        from calibre_plugins.bookfusion_autosync.config import ConfigWidget
        return ConfigWidget()

    def save_settings(self, config_widget):
        config_widget.save_settings()

        ac = self.actual_plugin_
        if ac is not None:
            ac.apply_settings()
