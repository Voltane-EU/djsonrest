import time
from jose import jwt
from django.db import models
from djutils.crypt import random_string_generator

from djsonrest import app_settings


def generate_token_id():
    return random_string_generator(size=64)


class Token(models.Model):
    @classmethod
    def _jwt_read_private_key(cls):
        with open(app_settings.JWT_PRIVATE_KEY_FILE) as key:
            return key.read()

    def create_jwt_claims(self, expire=None, **claims):
        curr_time = time.time()
        claims.update({
            'iss': app_settings.JWT_ISSUER,
            'iat': int(curr_time),
            'exp': int(curr_time + (expire or app_settings.JWT_DEFAULT_EXPIRE)),
            'aud': self.audience,
            'sub': self.subject,
        })
        return claims

    def create_jwt(self):
        claims = self.create_jwt_claims()
        token = jwt.encode(
            claims=claims,
            key=self._jwt_read_private_key(),
            algorithm=app_settings.JWT_SIGNING_ALGORITHM,
            access_token=app_settings.JWT_ACCESS_TOKEN,
        )
        return token, claims

    id = models.CharField(max_length=64, default=generate_token_id, primary_key=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    expire_at = models.DateTimeField()
    subject = models.CharField(max_length=128)
    audience = models.CharField(max_length=128)
