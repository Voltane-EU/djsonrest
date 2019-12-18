from django.conf import settings
from djsonrest import rest


class Default(rest.RESTRouteGroup):
    @rest.route('/', version=0.0, method='GET', name='default')
    def default(self, request, *args, **kwargs):
        return {
            "name": getattr(settings, "TITLE", None),
            "author": getattr(settings, "AUTHOR", None),
            "version": getattr(settings, "GIT_VERSION_HEX", None),
        }
