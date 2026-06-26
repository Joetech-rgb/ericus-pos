from django.utils import timezone
from datetime import timedelta
from django.conf import settings


def shop_profile(request):
    """
    Makes shop name, logo, and currency available in every template.
    Usage in template: {{ shop.name }}, {{ shop.logo.url }}, {{ shop.currency_symbol }}
    """
    shop = None
    if request.user.is_authenticated:
        try:
            from .models import ShopProfile
            shop = ShopProfile.objects.select_related('owner').first()
        except Exception:
            pass
    return {'shop': shop}


def users_online(request):
    """
    Makes online user count available in every template.
    Usage in template: {{ online_count }}
    """
    count = 0
    if request.user.is_authenticated and request.user.is_owner:
        try:
            from .models import UserSession
            timeout = getattr(settings, 'USER_ONLINE_TIMEOUT', 5)
            cutoff  = timezone.now() - timedelta(minutes=timeout)
            count   = UserSession.objects.filter(last_activity__gte=cutoff).count()
        except Exception:
            pass
    return {'online_count': count}