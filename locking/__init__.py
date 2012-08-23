VERSION = (0, 3, 0)
from django.conf import settings

# Time between updating the lock in seconds
LOCK_TIMEOUT = getattr(settings, 'LOCK_TIMEOUT', 180)
