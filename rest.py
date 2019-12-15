"""
Base Module of djsonrest containing interfaces to create rest routes
"""

import logging

from django.urls import path as url_path
from django.views.generic import View
from . import exceptions, auth as rest_auth


_logger = logging.getLogger(__name__)
rest_routes = {}


class RESTRouteVersionMethod:
    HTTP_METHODS = ('GET', 'POST', 'PUT', 'PATCH', 'DELETE')

    def __init__(
            self,
            route_func: callable,
            path: str = "",
            version=None,
            method: str = 'GET',
            auth: rest_auth.Authentication = rest_auth.Public,
            name: str = None,
            cache: callable = None,
        ):
        if not path:
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
        self.name = name
        self.cache = cache

        self.route_version = RESTRoute.get_route(self.path).get_version_route(self.version)
        self.route_version.register_method_route(self)

        _logger.debug("Registered new rest route %r", self)

    def __str__(self):
        return f"RESTRouteMethod<{self.method} {self.path}, version={self.version}, auth={self.auth}, name={self.name}>"

    def __call__(self, request, *args, **kwargs):
        """
        Wrapper around the actual view function
        """
        self.auth.authenticate(request)

        route_result = self.route_func(request, *args, **kwargs)
        return route_result

    def to_path(self):
        return url_path(self.path, self, name=self.name)


class RESTRouteVersion(View):
    get_cache = None

    def __init__(
            self,
            path: str = "",
            version=None,
            **kwargs,
        ):
        super().__init__(**kwargs)

        self.path = path
        self.version = version
        self.route = RESTRoute.get_route(self.path)

    def head(self, *args, **kwargs):
        if not self.get_cache:
            return None

        return self.get_cache()

    def register_method_route(self, method_route: RESTRouteVersionMethod):
        if hasattr(method_route.method.lower()):
            raise exceptions.InvalidRouteError('The method %s is already defined for this path and version' % method_route.method)

        setattr(self, method_route.method.lower(), method_route)

        if method_route.method == "GET" and method_route.cache:
            self.get_cache = method_route.cache


class RESTRoute:
    @staticmethod
    def pass_to_version(method: str):
        def get_version_method(self, version, *args, **kwargs):
            version_route = self.get_version_route(1.0)
            return getattr(version_route, method)(*args, **kwargs)

        return get_version_method

    @classmethod
    def get_route(cls, path):
        try:
            return rest_routes[path]
        except KeyError:
            return cls(path)

    def __init__(self, path: str):
        self.path = path
        self.version_routes = {}

        rest_routes[self.path] = self

    def get_version_route(self, version: tuple):
        try:
            return self.version_routes[version]
        except KeyError:
            return RESTRouteVersion(self.path, version)


    def find_matching_version_route(self, version: float):
        version_routes = list(filter(
            lambda vers_nr: (len(vers_nr) == 1 and vers_nr[0] <= version) or (len(vers_nr) == 2 and vers_nr[0] <= version <= vers_nr[1]),
            self.version_routes.keys()
        ))
        if len(version_routes) > 1:
            raise exceptions.InvalidRouteError("Found multiple routes for version %f" % version)

        return version_routes[0]

    head = pass_to_version('head')
    get = pass_to_version('get')
    post = pass_to_version('post')
    put = pass_to_version('put')
    patch = pass_to_version('patch')
    delete = pass_to_version('delete')


def route(
        path: str = "",
        version=None,
        method: str = 'GET',
        auth: rest_auth.Authentication = rest_auth.Public,
        name: str = None,
        cache: callable = None,
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
    name: optional name for the django route
    cache: optional callable, only for GET requests, to determine if the ressource has changed
    """
    def rest_route_wrapper(route_func):
        rest_route = RESTRouteVersionMethod(route_func, path, version, method, auth, cache)
        route_func._rest_route = rest_route
        return rest_route

    return rest_route_wrapper
