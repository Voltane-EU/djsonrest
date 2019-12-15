"""
Base Module of djsonrest containing interfaces to create rest routes
"""

import logging
import json

from django.urls import path as url_path, register_converter
from django.views.generic import View
from django.http.response import HttpResponse
from djutils.http import exceptions_to_http, respond_json
from . import exceptions, auth as rest_auth


_logger = logging.getLogger(__name__)
rest_routes = {}


class RESTVersionConverter:
    regex = r'\d\.\d{1,2}'

    @staticmethod
    def to_python(value):
        return float(value)

    @staticmethod
    def to_url(value):
        return "%.2f" % value


register_converter(RESTVersionConverter, 'rest_version')


class RESTRouteVersionMethod:
    HTTP_METHODS = ('GET', 'POST', 'PUT', 'PATCH', 'DELETE')

    def __init__(
            self,
            route_func: callable,
            path: str = "",
            version=None,
            method: str = 'GET',
            auth: rest_auth.Authentication = rest_auth.Public,
            cache: callable = None,
            name: str = None,
        ):
        if not path and name != "default":
            raise exceptions.InvalidRouteError('Undefined path for %r' % route_func)

        if method not in self.HTTP_METHODS:
            raise exceptions.InvalidRouteError('Invalid method for %r' % route_func)

        if not version:
            version = 1.0
        if isinstance(version, (float, int)):
            version = (version,)

        self.route_func = route_func
        self.path = path
        self.version = version
        self.method = method
        self.auth = auth(self)
        self.cache = cache
        self.name = name

        self.route_version = RESTRoute.get_route(self.path).get_version_route(self.version, self.name)
        self.route_version.register_method_route(self)

        _logger.debug("Registered new rest route %r", self)

    def __str__(self):
        return f"RESTRouteMethod<{self.method} {self.path}, version={self.version}, auth={self.auth}, name={self.name}>"

    @exceptions_to_http(exceptions.Error, status_code=400)
    @respond_json
    def __call__(self, request, *args, **kwargs):
        """
        Wrapper around the actual request method.
        Performs authentication and loads the request body as json into request.body (encoding is fixed to UTF-8).
        Returns a dict with 'data' containing the returned data from the request method,
        if 'data' is not already present.
        Also converts the response data to a JsonResponse using @djutils.http.respond_json
        """
        self.auth.authenticate(request)

        # Load and replace the request body as json data
        request.body_bytes = request.body
        if request.body:
            request.body = json.loads(request.body, encoding='utf-8')

        route_result = self.route_func(request, *args, **kwargs)

        if 'data' in route_result:
            return route_result

        return {'data': route_result}


class RESTRouteVersion:
    get_cache = None

    def __init__(
            self,
            path: str = "",
            version=None,
            name: str = None,
        ):
        if not isinstance(version, tuple) or not version:
            raise exceptions.InvalidRouteError('Invalid version "%r". Has to be a tuple containing at least one float value' % version)

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
            lambda vers_nr: (len(vers_nr) == 1 and vers_nr[0] <= version) or (len(vers_nr) == 2 and vers_nr[0] <= version <= vers_nr[1]),
            self.version_routes.keys()
        ))
        if len(version_routes) > 1:
            raise exceptions.InvalidRouteError("Found multiple routes for version %f" % version)

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
        path = "<rest_version:version>/%s" % self.path
        return url_path(path, self.RESTRouteView.as_view(rest_route=self, **kwargs), name=self.name)


def route(
        path: str = "",
        version=None,
        method: str = 'GET',
        auth: rest_auth.Authentication = rest_auth.Public,
        cache: callable = None,
        name: str = None,
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

    def rest_route_wrapper(route_func):
        rest_route = RESTRouteVersionMethod(route_func, path, version, method, auth, cache, name)
        route_func.rest_route = rest_route
        return route_func

    return rest_route_wrapper
