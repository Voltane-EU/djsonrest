"""
This module contains Database Models which persistently store data used for authentication.
"""

import uuid
import ipaddress
from datetime import timedelta
from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.conf import settings
from django.utils.functional import cached_property
from django.utils import timezone

from djsonrest import exceptions
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

    def check_rules(self, request):
        """
        Check that the given request is allowed by the consumers rules.
        Raises an exceptions.AuthenticationError when a rule forbids the access.
        """

        if not self.rules_active:
            return

        if 'ip' in self.rule_types:
            request_ip = ipaddress.ip_address(request.get_host())

            for denied_ip in self.denied_ips:
                if request_ip in ipaddress.ip_network(denied_ip):
                    raise exceptions.AuthenticationError

            for allowed_ip in self.allowed_ips:
                if request_ip in ipaddress.ip_network(allowed_ip):
                    continue
                raise exceptions.AuthenticationError

        if 'http_access_control_origin' in self.rule_types:
            origin = request.headers.get('origin')
            if not origin:
                raise exceptions.AuthenticationError

            if not self.rules.filter(type='http_access_control_origin', value=origin).count():
                raise exceptions.AuthenticationError

            request._rest_jwt_consumer_acao = origin

    @cached_property
    def allowed_ips(self):
        return self.rules.filter(type='ip', action='allow')

    @cached_property
    def denied_ips(self):
        return self.rules.filter(type='ip', action='deny')

    @cached_property
    def rule_types(self):
        return [rule['type'] for rule in self.rules.values('type').annotate(models.Count('pk'))]

    uid = models.UUIDField(primary_key=True, default=uuid.uuid4)
    key = models.CharField(max_length=128)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='consumer', help_text='Requests will be performed using this user')
    allowed_origin = models.CharField(max_length=255, help_text='Allowed origin which will be used in the Access-Control-Allow-Origin Header')
    tokens = models.ManyToManyField(Token, related_name='consumer')
    rules_active = models.BooleanField(default=False)


class ConsumerRule(models.Model):
    TYPES = (
        ('ip', 'IP Address'),
        ('http_access_control_origin', 'HTTP Access-Control-Origin'),
    )
    ACTION_TYPES = (
        ('allow', 'Allow'),
        ('deny', 'Deny'),
    )

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.type == 'ip':
            ip = ipaddress.ip_network(self.ip)
            self.value = str(ip)

        return super().save(force_insert, force_update, using, update_fields)

    consumer = models.ForeignKey(Consumer, on_delete=models.CASCADE, related_name='rules')
    type = models.CharField(max_length=32, choices=TYPES)
    value = models.CharField(max_length=255)
    action = models.CharField(max_length=6, choices=ACTION_TYPES)
