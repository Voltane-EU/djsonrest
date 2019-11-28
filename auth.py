"""
Authentication against the rest service.
"""

class Authentication:
    """
    Base of all authentication classes.
    This class is an abstract class; create a subclass of it to implement you auth functions.

    Raises AuthenticationError if authentication is invalid.
    """

    def __init__(self, rest_route):
        self.rest_route = rest_route

    def __str__(self):
        return self.__class__.__name__

    def authenticate(self, request):
        """
        Check the authentication of the current request.
        Raise a djrest.exceptions.AuthenticationError if it is invalid.
        """
        raise NotImplementedError


class Public(Authentication):
    def authenticate(self, request):
        return True


class JWTAuthentication(Authentication):
    def authenticate(self, request):
        pass
