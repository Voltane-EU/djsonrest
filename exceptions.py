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
    status_code = 401


class ConfigurationError(DJsonRestError):
    status_code = 500
