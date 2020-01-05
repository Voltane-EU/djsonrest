from datetime import timedelta
from django.db import models
from django.conf import settings
from django.utils import timezone
from .. import app_settings
from .token import Token


def user_create_token(user, audience='user_weak', lifetime=None, obtained_by=None):
    assert audience in ('user_weak', 'user_strong'), "The audience for user tokens has to be user_weak or user_strong"

    if not lifetime:
        if audience == 'user_strong':
            lifetime = app_settings.USER_STRONG_TOKEN_LIFETIME
        else:
            lifetime = app_settings.USER_WEAK_TOKEN_LIFETIME

    token = Token.objects.create(
        expire_at=timezone.now() + timedelta(seconds=lifetime),
        subject=str(user.pk),
        audience=audience,
    )
    user.user_tokens.create(token=token)

    if obtained_by:
        token.consumer.add(obtained_by)

    return token


class UserToken(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_tokens')
    token = models.OneToOneField(Token, on_delete=models.CASCADE, related_name='user_token')

    class Meta:
        unique_together = ['user', 'token',]
