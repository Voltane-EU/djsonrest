"""
Exceptions of djsonrest
"""

from djutils.exceptions import Error


class DJsonRestError(Error):
    """
    Base Error of djsonrest
    """


class InvalidRouteError(DJsonRestError):
    pass


class AuthenticationError(DJsonRestError):
    pass
