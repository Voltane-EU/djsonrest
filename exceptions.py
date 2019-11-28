"""
Exceptions of djREST
"""

from djutils.exceptions import Error


class DjRESTError(Error):
    """
    Base Error of djREST
    """


class InvalidRouteError(DjRESTError):
    pass


class AuthenticationError(DjRESTError):
    pass
