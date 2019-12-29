from django.conf import settings

JWT_ISSUER = getattr(settings, 'JWT_ISSUER', getattr(settings, 'TITLE', settings.SETTINGS_MODULE.split('.')[0]))
JWT_SIGNING_ALGORITHM = getattr(settings, 'JWT_SIGNING_ALGORITHM', 'ES512')
JWT_ACCESS_TOKEN = getattr(settings, 'JWT_ACCESS_TOKEN', None)
JWT_PRIVATE_KEY_FILE = getattr(settings, 'JWT_PRIVATE_KEY_FILE', None)
JWT_PUBLIC_KEY_FILE = getattr(settings, 'JWT_PUBLIC_KEY_FILE', None)
JWT_DEFAULT_EXPIRE = getattr(settings, 'JWT_DEFAULT_EXPIRE', 3600)

CONSUMER_TOKEN_LIFETIME = getattr(settings, 'JWT_CONSUMER_TOKEN_LIFETIME', 14400)
