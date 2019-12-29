from django.utils.module_loading import autodiscover_modules
from .rest import routes


def autodiscover():
    autodiscover_modules('rest_routes', register_to=routes)


default_app_config = 'djsonrest.apps.DJsonRestConfig'
