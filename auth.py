"""
Authentication against the rest service.
"""

import logging


_logger = logging.getLogger(__name__)


class Authentication:
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
