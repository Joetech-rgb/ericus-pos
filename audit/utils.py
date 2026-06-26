from .models import AuditLog


def log_action(
    user,
    category,
    action,
    description='',
    object_type='',
    object_id='',
    object_repr='',
    level=AuditLog.LEVEL_INFO,
    ip_address=None,
    request=None,
    **kwargs,   # ✅ absorbs unexpected kwargs like obj= so callers don't crash
):
    """
    Create an AuditLog entry from anywhere in the project.

    Usage:
        from audit.utils import log_action
        from audit.models import AuditLog

        log_action(
            user=request.user,
            category=AuditLog.CATEGORY_SALE,
            action=f'Completed sale #{sale.id}',
            object_type='Sale',
            object_id=str(sale.id),
            object_repr=str(sale),
            request=request,
        )
    """
    # Resolve IP from request if not provided directly
    if ip_address is None and request is not None:
        ip_address = _get_client_ip(request)

    username  = ''
    user_role = ''
    if user and user.is_authenticated:
        username  = user.username
        user_role = getattr(user, 'role', '')

    AuditLog.objects.create(
        user=user if (user and user.is_authenticated) else None,
        username=username,
        user_role=user_role,
        category=category,
        level=level,
        action=action,
        description=description,
        object_type=object_type,
        object_id=str(object_id) if object_id else '',
        object_repr=object_repr,
        ip_address=ip_address,
    )


def _get_client_ip(request):
    """Extract real IP, honouring X-Forwarded-For from proxies."""
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


# ── Convenience wrappers ─────────────────────────────────────────────────────

def log_auth(user, action, request=None, **kwargs):
    log_action(user, AuditLog.CATEGORY_AUTH, action, request=request, **kwargs)


def log_sale(user, action, request=None, **kwargs):
    log_action(user, AuditLog.CATEGORY_SALE, action, request=request, **kwargs)


def log_product(user, action, request=None, **kwargs):
    log_action(user, AuditLog.CATEGORY_PRODUCT, action, request=request, **kwargs)


def log_inventory(user, action, request=None, **kwargs):
    log_action(user, AuditLog.CATEGORY_INVENTORY, action, request=request, **kwargs)


def log_purchase(user, action, request=None, **kwargs):
    log_action(user, AuditLog.CATEGORY_PURCHASE, action, request=request, **kwargs)


def log_customer(user, action, request=None, **kwargs):
    log_action(user, AuditLog.CATEGORY_CUSTOMER, action, request=request, **kwargs)


def log_expense(user, action, request=None, **kwargs):
    log_action(user, AuditLog.CATEGORY_EXPENSE, action, request=request, **kwargs)


def log_return(user, action, request=None, **kwargs):
    log_action(user, AuditLog.CATEGORY_RETURN, action, request=request, **kwargs)


def log_wholesale(user, action, request=None, **kwargs):
    log_action(user, AuditLog.CATEGORY_WHOLESALE, action, request=request, **kwargs)


def log_user_mgmt(user, action, request=None, **kwargs):
    log_action(user, AuditLog.CATEGORY_USER, action, request=request, **kwargs)


def log_system(user_or_action, action=None, description='', level=AuditLog.LEVEL_INFO, request=None):
    """
    System-level events. Supports two call signatures:
      log_system(request.user, 'Some action', request=request)  ← new (with user)
      log_system('Some action', description='...')              ← old (no user)
    """
    # ✅ Handle both old signature (no user) and new signature (with user)
    if action is None:
        # Old-style: log_system('action string', description='...')
        user = None
        action = user_or_action
    else:
        # New-style: log_system(request.user, 'action string', request=request)
        user = user_or_action

    ip_address = _get_client_ip(request) if request else None
    username = user.username if user and user.is_authenticated else 'System'

    AuditLog.objects.create(
        user=user if (user and user.is_authenticated) else None,
        username=username,
        category=AuditLog.CATEGORY_SYSTEM,
        level=level,
        action=action,
        description=description,
        ip_address=ip_address,
    )


def get_recent_logs(limit=50, category=None, level=None, user=None):
    """Quick query helper used by dashboard widgets."""
    qs = AuditLog.objects.select_related('user')
    if category:
        qs = qs.filter(category=category)
    if level:
        qs = qs.filter(level=level)
    if user:
        qs = qs.filter(user=user)
    return qs[:limit]


def log_report(user, action, request=None, **kwargs):
    log_action(user, AuditLog.CATEGORY_REPORT, action, request=request, **kwargs)


def log_discount(user, action, request=None, **kwargs):
    log_action(user, AuditLog.CATEGORY_DISCOUNT, action, request=request, **kwargs)