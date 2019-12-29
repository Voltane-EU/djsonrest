"""
This module contains Database Models which persistently store data used for authentication.
"""

import uuid
import ipaddress
from datetime import timedelta
from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.conf import settings
from django.utils import timezone

from .token import Token
from .. import app_settings


class Consumer(models.Model):
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

    def set_key(self, key):
        self.key = self.key_hash(key)

    def create_token(self):
        return self.tokens.create(
            expire_at=timezone.now() + timedelta(seconds=app_settings.CONSUMER_TOKEN_LIFETIME),
            subject=str(self.uid),
            audience='consumer',
        )

    @property
    def allowed_ips(self):
        return self.ip_rules.filtered(type='allow')

    @property
    def denied_ips(self):
        return self.ip_rules.filtered(type='deny')

    uid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    key = models.CharField(max_length=128)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='consumer', help_text='Requests will be performed using this user')
    allowed_origin = models.CharField(max_length=255, help_text='Allowed origin which will be used in the Access-Control-Allow-Origin Header')
    tokens = models.ManyToManyField(Token, related_name='consumer')
    ip_rules_active = models.BooleanField(default=False)


class ConsumerIPRule(models.Model):
    RULE_TYPES = (
        ('allow', 'Allow'),
        ('deny', 'Deny'),
    )

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        ip = ipaddress.ip_network(self.ip)
        self.ip = str(ip)

        return super().save(force_insert, force_update, using, update_fields)

    consumer = models.ForeignKey(Consumer, on_delete=models.CASCADE, related_name='ip_rules')
    ip = models.CharField(max_length=196, help_text='IP Address or Subnet in CIDR Notation')
    type = models.CharField(max_length=8, choices=RULE_TYPES)
