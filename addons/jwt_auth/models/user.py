from django.db import models
from django.conf import settings
from .token import Token


class UserToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_tokens')
    token = models.OneToOneField(Token, on_delete=models.CASCADE, related_name='user_token')

    class Meta:
        unique_together = ['user', 'token',]
