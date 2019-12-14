"""
Base Module of djsonrest containing interfaces to create rest routes
"""

import logging

from django.urls import path as url_path
from django.views.generic import View
from . import exceptions, auth as rest_auth


_logger = logging.getLogger(__name__)
rest_routes = {}


class RESTRouteMethod:
    HTTP_METHODS = ('GET', 'POST', 'PUT', 'PATCH', 'DELETE')

    def __init__(
            self,
            route_func: callable,
            method: str = 'GET',
            path: str = "",
            version=None,
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
        self.method = method
        self.path = path
        self.version = version
        self.auth = auth(self)
        self.name = name
        self.cache = cache

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


class RESTRoute(View):
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

        rest_routes[(self.path, self.version,)] = self

    def head(self, *args, **kwargs):
        if not self.get_cache:
            return None

        return self.get_cache()

    @classmethod
    def register_method_route(cls, method_route: RESTRouteMethod):
        try:
            rest_route = rest_routes[(method_route.path, method_route.version)]
        except KeyError:
            rest_route = cls(method_route.path, method_route.version)

        if hasattr(method_route.method.lower()):
            raise exceptions.InvalidRouteError('The method %s is already defined for this path and version' % method_route.method)

        setattr(rest_route, method_route.method.lower(), method_route)

        if method_route.method == "GET" and method_route.cache:
            rest_route.get_cache = method_route.cache


def route(
        method: str = 'GET',
        path: str = "",
        version: float = None,
        auth: rest_auth.Authentication = rest_auth.Public,
        name: str = None,
        cache: callable = None,
    ):
    """
    Declare a method as rest endpoint.
    Params:
    method: The HTTP Method
    path: URL of the REST endpoint after the default path prefix and version number
    auth: Used authentication mechanism
    name: optional name for the django route
    cache: optional callable, only for GET requests, to determine if the ressource has changed
    """
    def rest_route_wrapper(route_func):
        rest_route = RESTRouteMethod(route_func, path, method, version, auth, cache)
        route_func._rest_route = rest_route
        return rest_route

    return rest_route_wrapper
