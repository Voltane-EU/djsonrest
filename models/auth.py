"""
This module contains Database Models which persistently store data used for authentication.
"""

import uuid
from django.db import models
from django.contrib.auth.hashers import make_password, check_password


class AuthConsumer(models.Model):
    uid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    key = models.CharField(max_length=128)
    user = models.OneToOneField('User', on_delete=models.CASCADE, related_name='consumer')

    @classmethod
    def key_hash(cls, key):
        """
        Hashes a key with the django hashing method and returns it
        """
        return make_password(key)

    def check_key(self, key):
        """
        Checks if a given key matches the stored key in the database.
        """
        return check_password(key, self.key)
