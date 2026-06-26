from django.utils.deprecation import MiddlewareMixin
from .models import AuditLog
from .utils import _get_client_ip

# URL patterns that should auto-generate an audit log entry.
# Format: (method, path_contains, category, action_template, level)
# action_template can use {user} as a placeholder.
WATCHED_PATTERNS = [
    # Auth
    ('POST', '/accounts/login/',    AuditLog.CATEGORY_AUTH,      'User logged in',         AuditLog.LEVEL_INFO),
    ('POST', '/accounts/logout/',   AuditLog.CATEGORY_AUTH,      'User logged out',        AuditLog.LEVEL_INFO),
    ('POST', '/accounts/pin/verify/', AuditLog.CATEGORY_AUTH,    'PIN verified',           AuditLog.LEVEL_INFO),

    # Sales — individual POST entries are logged manually in views for full detail.
    # We auto-log at the URL level only for deletes.
    ('POST', '/sales/void/',        AuditLog.CATEGORY_SALE,      'Sale voided',            AuditLog.LEVEL_WARNING),

    # Products
    ('POST', '/products/import/',   AuditLog.CATEGORY_PRODUCT,   'Bulk product import',    AuditLog.LEVEL_WARNING),

    # Reports
    ('GET',  '/reports/',           AuditLog.CATEGORY_REPORT,    'Viewed reports',         AuditLog.LEVEL_INFO),
]


class AuditMiddleware(MiddlewareMixin):
    """
    Silently watches certain URLs and writes AuditLog entries after a
    successful response (status < 400).

    Fine-grained logging (with object IDs, amounts, etc.) is done manually
    inside views using log_action() / the convenience wrappers in utils.py.
    This middleware handles the broad strokes so nothing gets missed.
    """

    def process_response(self, request, response):
        # Only log successful responses
        if response.status_code >= 400:
            return response

        # Skip AJAX calls — those views log their own actions
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return response

        user = getattr(request, 'user', None)
        if user is None or not user.is_authenticated:
            return response

        path = request.path
        method = request.method

        for watch_method, url_fragment, category, action, level in WATCHED_PATTERNS:
            if method == watch_method and url_fragment in path:
                username = user.username if user.is_authenticated else 'Anonymous'
                AuditLog.objects.create(
                    user=user,
                    username=username,
                    user_role=getattr(user, 'role', ''),
                    category=category,
                    level=level,
                    action=action.format(user=username),
                    ip_address=_get_client_ip(request),
                )
                break   # Only match the first pattern per request

        return response