"""
Base Module of djsonrest containing interfaces to create rest routes
"""

import logging
import json
import enum
import re

from django.urls import path as url_path, register_converter
from django.views.generic import View
from django.http.response import HttpResponse, Http404
from django.core import exceptions as django_exceptions
from djutils.http import error_respond_json, respond_json
from . import exceptions, auth as rest_auth, app_settings


_logger = logging.getLogger(__name__)
rest_routes = {}


class RESTVersionConverter:
    regex = r'(\d+)\.(\d{1,2})'

    @staticmethod
    def to_python(value):
        value = re.match(RESTVersionConverter.regex, value)
        return (int(value[1]), int(value[2]))

    @staticmethod
    def to_url(value):
        return "%i.%i" % value


register_converter(RESTVersionConverter, 'rest_version')


class RESTVersionMatch(enum.Enum):
    @classmethod
    def FOLLOWING_MINOR(cls, version, other: tuple):
        """ Inlcude all subsequent minor versions of the same major version """
        if other[0] != version.major:
            return False
        if other[1] < version.minor:
            return False

        return True

    @classmethod
    def EQUAL(cls, version, other: tuple):
        """ Include only this version """
        if version.number != other:
            return False

        return True

    @classmethod
    def FOLLOWING_MAJOR_MINOR(cls, version, other: tuple):
        """ Include all subsequent versions, including major version jumps """
        if other[0] < version.major:
            return False
        if other[0] == version.major and other[1] < version.minor:
            return False

        return True


class RESTVersion:
    def __init__(self, number, match: callable = RESTVersionMatch.FOLLOWING_MINOR):
        if isinstance(number, float):
            if round(number, 2) != number:
                raise exceptions.InvalidRouteError("Version number may has only 2 decimal places")

            self.major = int(number)
            minor = (number - self.major) * 10
            if round(minor) != minor:
                minor *= 10
            self.minor = int(minor)
            self.number = (self.major, self.minor)

        elif isinstance(number, tuple):
            self.major, self.minor = number
            self.number = number

        else:
            raise exceptions.InvalidRouteError("Define the version as a float (major.minor) or tuple out of two integers (major, minor)")

        self.match = match

    def matches(self, other):
        return self.match(self, other)

    def __gt__(self, other):
        return self.number > other.number

    def __lt__(self, other):
        return self.number < other.number

    def __eq__(self, other):
        return self.number == other.number

    def __str__(self):
        return f"RESTVersion({self.number}, match={self.match.__name__})"

    __repr__ = __str__

    def __hash__(self):
        return hash((self.number, self.match))


class RESTRouteVersionMethod:
    HTTP_METHODS = ('GET', 'POST', 'PUT', 'PATCH', 'DELETE')
    handled_exceptions = (exceptions.Error,)

    @classmethod
    def _exception_to_manageable_error(cls, error):
        return type(error.__class__.__name__, (exceptions.Error, error,), {})

    def exception_handler(self, request):
        try:
            try:
                yield

            except (django_exceptions.ObjectDoesNotExist, django_exceptions.FieldDoesNotExist) as error:
                raise self._exception_to_manageable_error(error)(*error.args[:2], status_code=404) from error

            except django_exceptions.ValidationError as error:
                raise self._exception_to_manageable_error(error)(
                    message=error.message,
                    code=error.code,
                    params=error.params,
                    status_code=400
                ) from error

            except django_exceptions.SuspiciousOperation as error:
                raise self._exception_to_manageable_error(error)(*error.args[:2], status_code=403) from error

        except self.handled_exceptions as error:
            _logger.exception(error)
            return error_respond_json(error, status_code=400)

    def __init__(
            self,
            route_func: callable,
            path: str = "",
            version=None,
            method: str = 'GET',
            auth: rest_auth.Authentication = rest_auth.Public,
            cache: callable = None,
            name: str = None,
            handled_exceptions: tuple = (),
        ):
        if not path and name != "default":
            raise exceptions.InvalidRouteError('Undefined path for %r' % route_func)

        if method not in self.HTTP_METHODS:
            raise exceptions.InvalidRouteError('Invalid method for %r' % route_func)

        if version is None:
            raise exceptions.InvalidRouteError("Specify a version for %r" % route_func)

        if isinstance(version, (float, int)):
            version = RESTVersion(float(version))
        elif not isinstance(version, RESTVersion):
            raise exceptions.InvalidRouteError("Specify the version using RESTVersion() or a single float or int for %r" % route_func)

        self.route_func = route_func
        self.path = path
        self.version = version
        self.method = method
        self.auth = auth(self)
        self.cache = cache
        self.name = name

        if not handled_exceptions and self.auth.handled_exceptions:
            handled_exceptions = self.auth.handled_exceptions
        if handled_exceptions:
            self.handled_exceptions += handled_exceptions

        self.route_version = RESTRoute.get_route(self.path).get_version_route(self.version, self.name)
        self.route_version.register_method_route(self)

        _logger.debug("Registered new rest route %r", self)

    def __str__(self):
        return f"RESTRouteMethod<{self.method} {self.path}, version={self.version}, auth={self.auth}, name={self.name}>"

    @respond_json
    def __call__(self, request, *args, **kwargs):
        """
        Wrapper around the actual request method.
        Performs authentication and loads the request body as json into request.body (encoding is fixed to UTF-8).
        Handles ocurring exceptions.
        Returns a dict with 'data' containing the returned data from the request method,
        if 'data' is not already present.
        Also converts the response data to a JsonResponse using @djutils.http.respond_json
        """

        with self.exception_hander(request):
            self.auth.authenticate(request)

            # Load and replace the request body as json data
            request.body_bytes = request.body
            if request.body:
                request.body = json.loads(request.body, encoding='utf-8')

            if self.route_func.rest_dec.func_owner:
                route_result = self.route_func(self.route_func.rest_dec.func_owner(), request, *args, **kwargs)
            else:
                route_result = self.route_func(request, *args, **kwargs)

            if 'data' in route_result:
                return route_result

            return {'data': route_result}


class RESTRouteVersion:
    get_cache = None

    def __init__(
            self,
            path: str = "",
            version: RESTVersion = None,
            name: str = None,
        ):
        self.path = path
        self.version = version
        self.name = name
        self.route = RESTRoute.get_route(self.path)
        self.route.version_routes[self.version] = self

    def head(self, *args, **kwargs):
        if not self.get_cache:
            return None

        return self.get_cache()

    def _default_method_handler(self, *args, **kwargs):
        return HttpResponse(status=405)

    get = _default_method_handler
    post = _default_method_handler
    put = _default_method_handler
    patch = _default_method_handler
    delete = _default_method_handler

    def register_method_route(self, method_route: RESTRouteVersionMethod):
        setattr(self, method_route.method.lower(), method_route)

        if method_route.method == "GET" and method_route.cache:
            self.get_cache = method_route.cache

        if method_route.name and not self.name:
            self.name = method_route.name


def _rest_route_pass_to_version(method: str):
    def rest_version_route(self, *args, version=None, **kwargs):
        version_route = self.rest_route.find_matching_version_route(version)
        self.request.rest_version = version_route
        self.request.rest_version_requested = version
        return getattr(version_route, method)(*args, **kwargs)

    return rest_version_route


class RESTRoute:

    @classmethod
    def get_route(cls, path):
        try:
            return rest_routes[path]
        except KeyError:
            return cls(path)

    def __init__(self, path: str, name: str = None):
        self.path = path
        self.name = name
        self.version_routes = {}

        rest_routes[self.path] = self

    def get_version_route(self, version: tuple, name: str = None):
        try:
            return self.version_routes[version]
        except KeyError:
            return RESTRouteVersion(self.path, version, name)


    def find_matching_version_route(self, version: float):
        version_routes = list(filter(
            lambda vers: vers.matches(version),
            self.version_routes.keys()
        ))
        version_routes = sorted(version_routes, reverse=True)

        if not version_routes:
            _logger.info("No Route found for version %r", version)
            raise Http404

        return self.version_routes[version_routes[0]]

    class RESTRouteView(View):
        rest_route = None

        def __init__(self, rest_route, **kwargs):
            super().__init__(**kwargs)
            self.rest_route = rest_route

        head = _rest_route_pass_to_version('head')
        get = _rest_route_pass_to_version('get')
        post = _rest_route_pass_to_version('post')
        put = _rest_route_pass_to_version('put')
        patch = _rest_route_pass_to_version('patch')
        delete = _rest_route_pass_to_version('delete')

    def as_path(self, **kwargs):
        path = f"{app_settings.VERSION_PREFIX}<rest_version:version>/{self.path}"
        return url_path(path, self.RESTRouteView.as_view(rest_route=self, **kwargs), name=self.name)


class RESTRouteDecorator:
    func_owner = None
    func_name = None

    class wrapper:
        def __init__(self, fn):
            self.fn = fn
            self.rest_dec = fn.rest_dec
            rest_route = RESTRouteVersionMethod(
                fn,
                self.rest_dec.path,
                self.rest_dec.version,
                self.rest_dec.method,
                self.rest_dec.auth,
                self.rest_dec.cache,
                self.rest_dec.name,
                self.rest_dec.handled_exceptions
            )
            fn.rest_route = rest_route

        def __set_name__(self, owner, name):
            self.rest_dec.func_owner = owner
            self.rest_dec.func_name = name

        def __get__(self, instance, owner):
            if callable(self.fn):
                def call(*args, **kwargs):
                    return self.fn(instance, *args, **kwargs)

                call.__name__ = self.fn.__name__
                return call
            return self.fn

        def __call__(self, *args, **kwargs):
            return self.fn(*args, **kwargs)

    def __init__(
            self,
            path: str = "",
            version=None,
            method: str = 'GET',
            auth: rest_auth.Authentication = rest_auth.Public,
            cache: callable = None,
            name: str = None,
            handled_exceptions: tuple = (),
        ):
        """
        Declare a method as rest endpoint.
        Params:
        method: The HTTP Method
        path: URL of the REST endpoint after the default path prefix and version number
        version: A tuple containing the minimum and maximum version number for this endpoint (example: (min, max,)).
                Can be a single float or int to only define the minimum version number.
                The version numbers may have a maximum of 2 decimal places.
        auth: Used authentication mechanism
        cache: optional callable, only for GET requests, to determine if the ressource has changed
        name: Optional name for the django route. Same for all versions and methods
        """

        if path.startswith("/"):
            path = path[1:]

        self.path = path
        self.version = version
        self.method = method
        self.auth = auth
        self.cache = cache
        self.name = name
        self.handled_exceptions = handled_exceptions

    def __call__(self, fn):
        fn.rest_dec = self
        return self.wrapper(fn)


class RESTRouteGroup:
    pass


route = RESTRouteDecorator
