from django.conf import settings
from djutils.http import error_respond_json
from djutils.exceptions import Error


class BadRequest(Error):
    pass


_bad_request = BadRequest(message="", code='bad_request')

def route_not_found(request, *args, **kwargs):
    return error_respond_json(_bad_request, status_code=400)


VERSION_PREFIX = getattr(settings, "REST_VERSION_PREFIX", "")
ROUTE_NOT_FOUND_VIEW = getattr(settings, "REST_ROUTE_NOT_FOUND_VIEW", route_not_found)
