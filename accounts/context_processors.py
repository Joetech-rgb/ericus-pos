from .models import ShopProfile, UserSession


def shop_profile(request):
    try:
        profile = ShopProfile.objects.first()
    except Exception:
        profile = None
    return {'shop_profile': profile}


def users_online(request):
    try:
        from django.utils import timezone
        from datetime import timedelta
        from django.conf import settings
        timeout = getattr(settings, 'USER_ONLINE_TIMEOUT', 5)
        cutoff = timezone.now() - timedelta(minutes=timeout)
        count = UserSession.objects.filter(last_seen__gte=cutoff).count()
    except Exception:
        count = 0
    return {'users_online_count': count}
