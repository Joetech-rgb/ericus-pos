"""Makes the Shop Details record available to every page as {{ site_shop }}."""


def site_shop(request):
    try:
        from .models import ShopProfile
        return {'site_shop': ShopProfile.objects.first()}
    except Exception:
        return {'site_shop': None}
