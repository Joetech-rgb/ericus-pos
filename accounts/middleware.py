from django.utils import timezone


class UserSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.user.is_authenticated:
            try:
                from .models import UserSession
                UserSession.objects.update_or_create(
                    user=request.user,
                    defaults={
                        'last_activity': timezone.now(),           # ← was 'last_seen' (wrong field)
                        'session_key': request.session.session_key or '',
                        'ip_address': _get_ip(request),
                        'device': request.META.get('HTTP_USER_AGENT', '')[:200],
                    }
                )
            except Exception:
                pass
        return response


def _get_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')