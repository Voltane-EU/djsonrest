import logging
from django.core import exceptions as django_exceptions
from djutils.http import error_respond_json


_logger = logging.getLogger(__name__)


class RESTRoutesMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, error):
        if not hasattr(request, "rest_request"):
            return

        try:
            if isinstance(error, (django_exceptions.ObjectDoesNotExist, django_exceptions.FieldDoesNotExist)):
                raise self._exception_to_manageable_error(error)(*error.args[:2], status_code=404) from error

            if isinstance(error, django_exceptions.ValidationError):
                raise self._exception_to_manageable_error(error)(
                    message=error.message,
                    code=error.code,
                    params=error.params,
                    status_code=400
                ) from error

            if isinstance(error, django_exceptions.SuspiciousOperation):
                raise self._exception_to_manageable_error(error)(*error.args[:2], status_code=403) from error

            raise error

        except request.rest_request.handled_exceptions as handled_error:
            _logger.exception(handled_error)
            return error_respond_json(handled_error, status_code=400)

        except Exception as handled_error: # pylint: disable=broad-except  # catch any other exception to return a nice json error message
            _logger.exception(handled_error)
            return error_respond_json(handled_error, status_code=500)


class RESTRoutesAccessControlMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['Access-Control-Allow-Origin'] = response.get('Access-Control-Allow-Origin', '*')
        response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response['Access-Control-Allow-Credentials'] = 'true'
        return response
