from django.apps import AppConfig


class DJsonRestConfig(AppConfig):
    name = 'djsonrest'
    verbose_name = 'djsonREST'

    def ready(self):
        super().ready()
        self.module.autodiscover()
