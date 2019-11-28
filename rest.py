"""
Base Module of djrest containing interfaces to create rest routes
"""

import logging

from django.urls import path as url_path
from . import exceptions, auth as rest_auth


_logger = logging.getLogger(__name__)
rest_routes = []


class RESTRoute:
    def __init__(
            self,
            route_func: callable,
            method: str = 'GET',
            path: str = "",
            version: float = None,
            auth: rest_auth.Authentication = rest_auth.Public,
            name: str = None,
        ):
        if not path:
            raise exceptions.InvalidRouteError

        self.route_func = route_func
        self.method = method
        self.path = path
        self.version = version
        self.auth = auth(self)
        self.name = name

        rest_routes.append(self)
        _logger.debug("Registered new rest route %r", self)

    def __str__(self):
        return f"RESTRoute<{self.method} {self.path}, version={self.version}, auth={self.auth}, name={self.name}>"

    def __call__(self, request, *args, **kwargs):
        """
        Wrapper around the actual view function
        """
        self.auth.authenticate(request)

        route_result = self.route_func(request, *args, **kwargs)
        return route_result

    def to_path(self):
        return url_path(self.path, self, name=self.name)


def route(
        method: str = 'GET',
        path: str = "",
        version: float = None,
        auth: rest_auth.Authentication = rest_auth.Public,
        name: str = None
    ):
    def rest_route_wrapper(route_func):
        rest_route = RESTRoute(route_func, path, method, version, auth)
        route_func._rest_route = rest_route
        return rest_route

    return rest_route_wrapper
