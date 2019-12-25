from django.conf import settings


VERSION_PREFIX = getattr(settings, "REST_VERSION_PREFIX", "")
