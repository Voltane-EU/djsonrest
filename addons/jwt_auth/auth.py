"""
Authentication using JWT (Json Web Tokens) in Authorization Header
"""

import logging
from jose import jwt
from jose.exceptions import JOSEError
from django.utils.translation import gettext_noop
from django.core.exceptions import ObjectDoesNotExist
from djsonrest.auth import Authentication
from djsonrest import exceptions
from . import app_settings
from .models import Token


_logger = logging.getLogger(__name__)


class AbstractJWTAuthentication(Authentication):
    __public_key = None

    audience = None
    public_key_file = app_settings.JWT_PUBLIC_KEY_FILE
    algorithm = app_settings.JWT_SIGNING_ALGORITHM
    access_token = app_settings.JWT_ACCESS_TOKEN
    issuer = app_settings.JWT_ISSUER

    @property
    def public_key(self):
        if self.__public_key:
            return self.__public_key

        if not self.public_key_file:
            raise exceptions.ConfigurationError('JWT Public Key not configured. Check your settings.')

        with open(self.public_key_file) as file:
            self.__public_key = file.read()

        return self.__public_key

    def authenticate(self, request):
        try:
            auth_header = request.headers['Authorization']
            auth_type, token = auth_header.split(" ")
            if auth_type != "Bearer":
                raise exceptions.AuthenticationError('Authentication token malformed')
        except (KeyError, ValueError,) as error:
            raise exceptions.AuthenticationError('Authentication token required') from error

        options = {}
        if not self.audience:
            options['verify_aud'] = False

        try:
            decoded_token = jwt.decode(
                token=token,
                key=self.public_key,
                algorithms=self.algorithm,
                audience=self.audience,
                issuer=self.issuer,
                access_token=self.access_token,
                options=options,
            )
        except jwt.ExpiredSignatureError as error:
            _logger.debug("Tried authentication with an expired token: %e", error)
            raise exceptions.AuthenticationError(gettext_noop('Session expired'), code='session_expired') from error
        except JOSEError as error:
            _logger.warning("Tried authentication with an invalid token: %e", error)
            raise exceptions.AuthenticationError(gettext_noop('Invalid authentication token'), code='token_invalid') from error

        return decoded_token


class Consumer(AbstractJWTAuthentication):
    audience = 'consumer'

    def authenticate(self, request):
        decoded_token = super().authenticate(request)

        try:
            token = Token.objects.get(id=decoded_token['jti'])
        except (ObjectDoesNotExist, KeyError) as error:
            raise exceptions.AuthenticationError from error

        request.rest_consumer = token.consumer.first()
        request.rest_consumer.check_rules(request)
        request.user = request.rest_consumer.user

        return decoded_token

    def response(self, request, response):
        try:
            response['Access-Control-Allow-Origin'] = request._rest_jwt_consumer_acao
            response['Vary'] = ("%s Origin" % response.get('Vary', '')).strip()
        except AttributeError:
            pass

        return response


class User(AbstractJWTAuthentication):

    def authenticate(self, request):
        decoded_token = super().authenticate(request)

        if not self.audience and decoded_token.get('aud') not in ('user_strong', 'user_weak',):
            raise exceptions.AuthenticationError

        try:
            token = Token.objects.get(id=decoded_token['jti'])
        except (ObjectDoesNotExist, KeyError) as error:
            raise exceptions.AuthenticationError from error

        request.user = token.user_token.user

        return decoded_token


class UserStrong(User):
    audience = 'user_strong'


class UserWeak(User):
    audience = 'user_weak'
