from django.conf import settings
from djsonrest import rest


@rest.route('/', version=1.0, method='GET', name='default')
def default(request, *args, **kwargs):
    return {
        "name": getattr(settings, "TITLE", None),
        "author": getattr(settings, "AUTHOR", None),
        "version": getattr(settings, "GIT_VERSION_HEX", None),
    }
