from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from datetime import timedelta
from django.conf import settings


def hash_pin(raw_pin):
    """Hash a raw PIN string for safe storage."""
    return make_password(raw_pin)


def verify_pin(raw_pin, hashed_pin):
    """Check a raw PIN against a stored hash. Returns True/False."""
    return check_password(raw_pin, hashed_pin)


def get_online_users():
    """Return queryset of currently online users."""
    from .models import UserSession
    timeout = getattr(settings, 'USER_ONLINE_TIMEOUT', 5)
    cutoff  = timezone.now() - timedelta(minutes=timeout)
    return UserSession.objects.filter(
        last_activity__gte=cutoff
    ).select_related('user')


def get_shop():
    """Return the single ShopProfile instance."""
    from .models import ShopProfile
    return ShopProfile.objects.select_related('owner').first()


def is_pin_locked(user):
    """Check if the owner PIN is currently locked."""
    try:
        return user.pin.is_locked
    except Exception:
        return False