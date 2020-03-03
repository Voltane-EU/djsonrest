"""
Base Module of djsonrest containing interfaces to create rest routes
"""

import logging
import json
import enum
import re

from django.urls import path as url_path, re_path, register_converter
from django.views.generic import View
from django.http.response import HttpResponse, JsonResponse
from django.utils.decorators import classonlymethod
from djutils.http import respond_json
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

    def __init__(
            self,
            route_func: callable,
            path: str = "",
            version=None,
            method: str = 'GET',
            auth: rest_auth.Authentication = rest_auth.Public,
            response_status: int = 200,
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
        self.response_status = response_status
        self.cache = cache
        self.name = name

        if not handled_exceptions and self.auth.handled_exceptions:
            handled_exceptions = self.auth.handled_exceptions
        if handled_exceptions:
            self.handled_exceptions += handled_exceptions

        self.route_version = RESTRoute.get_route(self.path).get_version_route(self.version, self.name)
        self.route_version.register_method_route(self)

        _logger.debug("Registered new rest route %r", self)

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

        request.rest_request = self
        cache_response = None

        self.auth.authenticate(request)

        if request.method != 'GET':
            try:
                request.JSON = json.loads(request.body, encoding='utf-8') if request.body else {}
            except json.JSONDecodeError as error:
                raise exceptions.EncodingError(error.args[0]) from error

        elif request.body:
            # GET Request with a request body
            raise exceptions.RequestError("A GET request may not have a request body")
        else:
            if not self.cache and self.route_func.rest_dec.cache:
                fn = self.route_func.rest_dec.cache
                if self.route_func.rest_dec.func_owner:
                    self.cache = lambda *args, **kwargs: fn(self.route_func.rest_dec.func_owner(), *args, **kwargs)

                else:
                    self.cache = fn

            if self.cache:
                # GET Request and cache function available
                cache_response = self.cache(request, *args, **kwargs)

        route_result = None

        if self.route_func.rest_dec.func_owner:
            route_result = self.route_func(self.route_func.rest_dec.func_owner(), request, *args, **kwargs)
        else:
            route_result = self.route_func(request, *args, **kwargs)

        if not (isinstance(route_result, dict) and 'data' in route_result):
            route_result = {'data': route_result}

        response = JsonResponse(route_result, safe=False, status=self.response_status)

        if cache_response:
            try:
                response['ETag'] = cache_response['ETag']
            except KeyError: # pylint: disable=except-pass
                pass

            try:
                response['Last-Modified'] = cache_response['Last-Modified']
            except KeyError: # pylint: disable=except-pass
                pass

        return self.auth.response(request, response)

    def __str__(self):
        return f"RESTRouteVersionMethod({self.method} {self.path} @ {self.version}, auth={self.auth})"

    __repr__ = __str__


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
        self.method_routes = {}

    def head(self, request, *args, **kwargs):
        if not self.get_cache:
            return None

        return self.get_cache(request, *args, **kwargs)

    def _default_method_handler(self, *args, **kwargs):
        return HttpResponse(status=405)

    get = _default_method_handler
    post = _default_method_handler
    put = _default_method_handler
    patch = _default_method_handler
    delete = _default_method_handler

    def register_method_route(self, method_route: RESTRouteVersionMethod):
        setattr(self, method_route.method.lower(), method_route)
        self.method_routes[method_route.method] = method_route

        if method_route.method == "GET" and method_route.cache:
            self.get_cache = method_route.cache

        if method_route.name and not self.name:
            self.name = method_route.name

    def __str__(self):
        return f"RESTRouteVersion({self.path} @ {self.version})"

    __repr__ = __str__


def _rest_route_pass_to_version(method: str):
    def rest_version_route(self, *args, version=None, **kwargs):
        version_route = self.rest_route.find_matching_version_route(version)
        self.request.rest_version = version_route
        self.request.rest_version_requested = version
        try:
            return getattr(version_route, method)(*args, **kwargs)
        except AttributeError:
            if hasattr(version_route, method):
                # error not caused by getattr(), may be caused inside call of route function, so reraise it
                raise

            return getattr(super(self.__class__, self), method)(*args, **kwargs)

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

    def get_version_route(self, version, name: str = None):
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
            return app_settings.ROUTE_NOT_FOUND_VIEW

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
        options = _rest_route_pass_to_version('options')

        @classonlymethod
        def as_view(cls, **initkwargs):
            view = super().as_view(**initkwargs)
            view.csrf_exempt = True
            return view

        def __str__(self):
            return f"RESTRouteView for {self.rest_route}"

        __repr__ = __str__

    def as_path(self, **kwargs):
        route_path = f"{app_settings.VERSION_PREFIX}<rest_version:version>/{self.path}"
        return url_path(route_path, self.RESTRouteView.as_view(rest_route=self, **kwargs), name=self.name)

    def __str__(self):
        return f"RESTRoute({self.path}, name={self.name})"

    __repr__ = __str__


class RESTRouteGroup:
    pass


class RESTApp:
    def __init__(self, version: RESTVersion = None, auth: rest_auth.Authentication = rest_auth.Public, name: str = None):
        self.version = version
        self.auth = auth
        self.name = name
        self.routes = []

    class RouteGroup(RESTRouteGroup):
        pass

    def route(self, *args, **kwargs):
        kwargs.update(app=self)
        if not kwargs.get('version'):
            kwargs.update(version=self.version)

        if not kwargs.get('auth'):
            kwargs.update(auth=self.auth)

        return RESTRouteDecorator(*args, **kwargs)

    def get(
            self,
            path: str = "",
            version=None,
            auth: rest_auth.Authentication = None,
            response_status: int = 200,
            cache: callable = None,
            name: str = None,
            handled_exceptions: tuple = (),
            **kwargs,
        ):
        kwargs.update(method="GET", path=path, version=version, auth=auth, response_status=response_status, cache=cache, name=name, handled_exceptions=handled_exceptions)
        return self.route(**kwargs)

    def post(
            self,
            path: str = "",
            version=None,
            auth: rest_auth.Authentication = None,
            response_status: int = 200,
            name: str = None,
            handled_exceptions: tuple = (),
            **kwargs,
        ):
        kwargs.update(method="POST", path=path, version=version, auth=auth, response_status=response_status, name=name, handled_exceptions=handled_exceptions)
        return self.route(**kwargs)

    def put(
            self,
            path: str = "",
            version=None,
            auth: rest_auth.Authentication = None,
            response_status: int = 200,
            name: str = None,
            handled_exceptions: tuple = (),
            **kwargs,
        ):
        kwargs.update(method="PUT", path=path, version=version, auth=auth, response_status=response_status, name=name, handled_exceptions=handled_exceptions)
        return self.route(**kwargs)

    def patch(
            self,
            path: str = "",
            version=None,
            auth: rest_auth.Authentication = None,
            response_status: int = 200,
            name: str = None,
            handled_exceptions: tuple = (),
            **kwargs,
        ):
        kwargs.update(method="PATCH", path=path, version=version, auth=auth, response_status=response_status, name=name, handled_exceptions=handled_exceptions)
        return self.route(**kwargs)

    def delete(
            self,
            path: str = "",
            version=None,
            auth: rest_auth.Authentication = None,
            response_status: int = 200,
            name: str = None,
            handled_exceptions: tuple = (),
            **kwargs,
        ):
        kwargs.update(method="DELETE", path=path, version=version, auth=auth, response_status=response_status, name=name, handled_exceptions=handled_exceptions)
        return self.route(**kwargs)


class RESTRouteDecorator:
    func_owner = None
    func_name = None

    class Wrapper:
        def __init__(self, fn):
            self.fn = fn
            self.rest_dec = fn.rest_dec
            self.rest_route = RESTRouteVersionMethod(
                fn,
                self.rest_dec.path,
                self.rest_dec.version,
                self.rest_dec.method,
                self.rest_dec.auth,
                self.rest_dec.response_status,
                self.rest_dec.cache,
                self.rest_dec.name,
                self.rest_dec.handled_exceptions
            )
            fn.rest_route = self.rest_route

            if self.rest_dec.app:
                self.rest_dec.app.routes.append(self.rest_route)

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

        def cache(self, fn):
            """
            Define a cache method for a existing route
            """
            assert self.rest_dec.method == "GET"
            self.rest_dec.cache = fn

    def __init__(
            self,
            path: str = "",
            version=None,
            method: str = 'GET',
            auth: rest_auth.Authentication = rest_auth.Public,
            response_status: int = 200,
            cache: callable = None,
            name: str = None,
            handled_exceptions: tuple = (),
            app: RESTApp = None,
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
        cache: optional callable, only for GET requests, to determine if the ressource has changed.
               The callable has to return a django HTTPResponse containing an ETag or Last-Modified (or both) header
        name: Optional name for the django route. Same for all versions and methods
        """

        if path.startswith("/"):
            path = path[1:]

        self.path = path
        self.version = version
        self.method = method
        self.auth = auth
        self.response_status = response_status
        self.cache = cache
        self.name = name
        self.handled_exceptions = handled_exceptions
        self.app = app

    def __call__(self, fn):
        fn.rest_dec = self
        return self.Wrapper(fn)


class RESTRouteDecoratorMethod(RESTRouteDecorator):
    method = None

    def __init__(
            self,
            path: str = "",
            version=None,
            auth: rest_auth.Authentication = rest_auth.Public,
            response_status: int = 200,
            cache: callable = None,
            name: str = None,
            handled_exceptions: tuple = (),
            app: RESTApp = None,
        ):
        super().__init__(
            path=path,
            version=version,
            method=self.method,
            auth=auth,
            response_status=response_status,
            cache=cache,
            name=name,
            handled_exceptions=handled_exceptions,
            app=app,
        )


class RESTRouteDecoratorMethodGET(RESTRouteDecoratorMethod):
    method = 'GET'


class RESTRouteDecoratorMethodPOST(RESTRouteDecoratorMethod):
    method = 'POST'


class RESTRouteDecoratorMethodPUT(RESTRouteDecoratorMethod):
    method = 'PUT'


class RESTRouteDecoratorMethodPATCH(RESTRouteDecoratorMethod):
    method = 'PATCH'


class RESTRouteDecoratorMethodDELETE(RESTRouteDecoratorMethod):
    method = 'DELETE'


class RESTRoutes:
    def __init__(self):
        self._registry = {}

    @property
    def urls(self):
        urlpatterns = [
            route.as_path() for route in rest_routes.values()
        ]
        urlpatterns += [
            re_path(r"^(?P<path>.*)$", app_settings.ROUTE_NOT_FOUND_VIEW),
            url_path("", app_settings.ROUTE_NOT_FOUND_VIEW),
        ]

        return urlpatterns, 'djsonrest', 'djsonrest'


def remove(path: str, version: RESTVersion = None, method: str = None):
    """
    Remove a defined rest route from the routing.
    Specify at least the path; can be further filtered by specifying version and method.
    """

    if path.startswith("/"):
        path = path[1:]

    if method and version:
        assert method in RESTRouteVersionMethod.HTTP_METHODS, "Invalid method"
        route_version = rest_routes[path].version_routes[version]
        setattr(route_version, method.lower(), getattr(route_version, '_default_method_handler'))
    elif version:
        if not isinstance(version, RESTVersion):
            version = RESTVersion(version)
        del rest_routes[path].version_routes[version]
    else:
        del rest_routes[path]

    _logger.debug('Removed route "%s", version=%s, method=%s', path, version or 'any', method or 'any')


route = RESTRouteDecorator

get = RESTRouteDecoratorMethodGET
post = RESTRouteDecoratorMethodPOST
put = RESTRouteDecoratorMethodPUT
patch = RESTRouteDecoratorMethodPATCH
delete = RESTRouteDecoratorMethodDELETE

routes = RESTRoutes()
