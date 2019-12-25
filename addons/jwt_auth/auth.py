"""
Authentication using JWT (Json Web Tokens) in Authorization Header
"""

import logging
from jose import jwt
from jose.exceptions import JOSEError
from django.utils.translation import gettext_noop
from djsonrest.auth import Authentication
from djsonrest import exceptions
from . import app_settings


_logger = logging.getLogger(__name__)


class AbstractJWTAuthentication(Authentication):
    audience = None
    public_key_file = app_settings.JWT_PUBLIC_KEY_FILE
    algorithm = app_settings.JWT_SIGNING_ALGORITHM
    access_token = app_settings.JWT_ACCESS_TOKEN
    issuer = app_settings.JWT_ISSUER

    @property
    def public_key(self):
        with open(self.public_key_file) as file:
            self.public_key = file.read()

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
        except JOSEError as error:
            _logger.warning("Tried authentication with an invalid token: %e", error)
            raise exceptions.AuthenticationError(gettext_noop('Invalid authentication token'), code='token_invalid') from error

        return decoded_token
