from django.db import models
from jose import jwt
from djutils.crypt import random_string_generator


def generate_token_id():
    return random_string_generator(size=64)


class Token(models.Model):
    id = models.CharField(max_length=64, default=generate_token_id, primary_key=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    expire_at = models.DateTimeField()
    subject = models.CharField(max_length=128)
    audience = models.CharField(max_length=128)
