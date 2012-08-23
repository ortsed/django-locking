VERSION = (0, 3, 0)

from django.conf import settings
LOCK_TIMEOUT = getattr(settings, 'LOCK_TIMEOUT', 600)
