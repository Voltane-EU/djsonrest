"""
This module contains Database Models which persistently store data used for authentication.
"""

import uuid
from django.db import models
from django.contrib.auth import get_user_model


UserModel = get_user_model()


class AuthConsumer(UserModel):
    uid = models.UUIDField(primary_key=True, default=uuid.uuid4)
