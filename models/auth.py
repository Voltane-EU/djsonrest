"""
This module contains Database Models which persistently store data used for authentication.
"""

import uuid
import ipaddress
from django.db import models
from django.contrib.auth.hashers import make_password, check_password


class AuthConsumer(models.Model):
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

    @property
    def allowed_ips(self):
        return self.ip_rules.filtered(type='allow')

    @property
    def denied_ips(self):
        return self.ip_rules.filtered(type='deny')

    uid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    key = models.CharField(max_length=128)
    user = models.OneToOneField('User', on_delete=models.CASCADE, related_name='consumer')
    allowed_origin = models.CharField(max_length=255, help_text='Allowed origin which will be used in the Access-Control-Allow-Origin Header')
    tokens = models.ManyToManyField('djsonrest.Token', related_name='consumer')


class AuthConsumerIPRule(models.Model):
    RULE_TYPES = (
        ('allow', 'Allow'),
        ('deny', 'Deny'),
    )

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        ip = ipaddress.ip_network(self.ip)
        self.ip = str(ip)

        return super().save(force_insert, force_update, using, update_fields)

    consumer = models.ForeignKey(AuthConsumer, on_delete=models.CASCADE, related_name='ip_rules')
    ip = models.CharField(max_length=196, help_text='IP Address or Subnet in CIDR Notation')
    type = models.CharField(max_length=8, choices=RULE_TYPES)
