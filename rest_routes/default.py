from django.conf import settings
from djsonrest import rest


class Default(rest.RESTRouteGroup):
    @rest.get('/', version=rest.RESTVersion(0.0, match=rest.RESTVersionMatch.FOLLOWING_MAJOR_MINOR), name='default')
    def default(self, request, *args, **kwargs):
        return {
            "name": getattr(settings, "TITLE", None),
            "author": getattr(settings, "AUTHOR", None),
            "version": getattr(settings, "GIT_VERSION_HEX", None),
        }
