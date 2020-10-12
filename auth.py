"""
Authentication against the rest service.
"""

import logging
from django.http import HttpResponse
from . import exceptions


_logger = logging.getLogger(__name__)


class AuthenticationMeta(type):
    def __or__(cls, other):
        return HybridAuth(cls, other, operator="or")


class Authentication(metaclass=AuthenticationMeta):
    """
    Base of all authentication classes.
    This class is an abstract class; create a subclass of it to implement you auth functions.

    Raises AuthenticationError if authentication is invalid.
    """

    handled_exceptions = ()

    def __init__(self, rest_route):
        self.rest_route = rest_route

    def __str__(self):
        return self.__class__.__name__

    def authenticate(self, request):
        """
        Check the authentication of the current request.
        Raise a djsonrest.exceptions.AuthenticationError if it is invalid.
        It may return anything, but it will never be returned to the user directly,
        but it can be used to create extendable classes.
        """
        raise NotImplementedError

    def response(self, request, response):
        """
        Wrapper to manipulate the successfull response before returning it.
        Returns a django response object
        """
        return response


class Public(Authentication):
    def authenticate(self, request):
        return True


class HybridAuth(Authentication):
    def __init__(self, *args, operator="or"): # pylint: disable=super-init-not-called
        """
        Authentication using different available auth methods.
        Instanciate this class and give the authentication methods as arguments.
        For operator = or:
            The methods are tried in the order given in *args; when the authentication fails, the next is tried.
            If all authentications fail, the hybrid auth will also fail.
        """
        assert operator in ("or", "and")

        self.auth_methods = args
        self.operator = operator
        self.auth_used = None

    def __call__(self, rest_route):
        self.rest_route = rest_route
        return self

    def __str__(self):
        return "HybridAuth(%s)" % (" %s " % self.operator).join([auth.__name__ for auth in self.auth_methods])

    @property
    def handled_exceptions(self):
        if not self.auth_used:
            return ()

        return self.auth_used.handled_exceptions

    def authenticate(self, request):
        if self.operator == "or":
            for auth in self.auth_methods:
                try:
                    auth_instance = auth(self.rest_route)
                    auth_instance.authenticate(request)
                    self.auth_used = auth_instance
                    return

                except exceptions.AuthenticationError:
                    pass

        elif self.operator == "and":
            raise NotImplementedError

        raise exceptions.AuthenticationError

    def response(self, request, response: HttpResponse) -> HttpResponse:
        if not self.auth_used:
            return response

        return self.auth_used.response(request, response)
