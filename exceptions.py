"""
Exceptions of djsonrest
"""

from djutils.exceptions import Error


class DJsonRestError(Error):
    """
    Base Error of djsonrest
    """

    def __init__(self, message="", code=None, status_code=None, **kw):
        super().__init__(message, code, status_code, **kw)


class AuthenticationError(DJsonRestError):
    status_code = 401


class AccessError(DJsonRestError):
    status_code = 403


class ConfigurationError(DJsonRestError):
    status_code = 500


class EncodingError(DJsonRestError):
    status_code = 400


class RequestError(DJsonRestError):
    status_code = 400


class InvalidRouteError(Exception):
    pass
