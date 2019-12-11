"""
Authentication against the rest service.
"""

import logging
from jose import jwt
from django.conf import settings
from django.utils.translation import gettext_noop
from django.core.exceptions import ObjectDoesNotExist
from . import exceptions, models


_logger = logging.getLogger(__name__)


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
        Raise a djsonrest.exceptions.AuthenticationError if it is invalid.
        It may return anything, but it will never be returned to the user directly,
        but it can be used to create extendable classes.
        """
        raise NotImplementedError


class Public(Authentication):
    def authenticate(self, request):
        return True


class JWTAuthentication(Authentication):
    audience = None
    public_key_file = None
    private_key_file = None
    algorithm = 'ES512'
    access_token = None
    issuer = settings.TITLE

    @property
    def public_key(self):
        with open(self.public_key_file) as file:
            self.public_key = file.read()

    @property
    def private_key(self):
        with open(self.private_key_file) as file:
            self.private_key = file.read()

    def authenticate(self, request):
        token = None

        try:
            decoded_token = jwt.decode(
                token=token,
                key=self.public_key,
                algorithms=self.algorithm,
                audience=self.audience,
                issuer=self.issuer,
                access_token=self.access_token,
            )
        except jwt.ExpiredSignatureError as error:
            _logger.debug("Tried authentication with an expired token: %e", error)
            raise exceptions.AuthenticationError(gettext_noop('Session expired'), code='session_expired') from error
        except jwt.JWTError as error:
            _logger.warning("Tried authentication with an invalid token: %e", error)
            raise exceptions.AuthenticationError(gettext_noop('Invalid authentication token'), code='signature_invalid') from error

        return decoded_token


class JWTConsumer(JWTAuthentication):
    audience = 'consumer'

    def authenticate(self, request):
        decoded_token = super().authenticate(request)
        try:
            consumer = models.AuthConsumer.objects.get()
        except ObjectDoesNotExist as error:
            raise exceptions.AuthenticationError(gettext_noop('Invalid consumer'), code='consumer_invalid') from error

        # TODO: Check session (maybe optional, configured by consumer)

        return decoded_token
