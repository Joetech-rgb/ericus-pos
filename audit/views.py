import csv
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET

from accounts.decorators import owner_required
from .models import AuditLog


@owner_required
def audit_log_list(request):
    """
    Owner-only view. Full audit trail with search, filter by category,
    level, date range, and user.
    """
    logs = AuditLog.objects.select_related('user').all()

    # ── Filters ──────────────────────────────────────────────────────────────
    search   = request.GET.get('q', '').strip()
    category = request.GET.get('category', '').strip()
    level    = request.GET.get('level', '').strip()
    username = request.GET.get('user', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to   = request.GET.get('date_to', '').strip()

    if search:
        logs = logs.filter(action__icontains=search) | \
               logs.filter(description__icontains=search) | \
               logs.filter(object_repr__icontains=search)

    if category:
        logs = logs.filter(category=category)

    if level:
        logs = logs.filter(level=level)

    if username:
        logs = logs.filter(username__icontains=username)

    if date_from:
        try:
            logs = logs.filter(timestamp__date__gte=date_from)
        except ValueError:
            pass

    if date_to:
        try:
            logs = logs.filter(timestamp__date__lte=date_to)
        except ValueError:
            pass

    # ── Quick date shortcuts ──────────────────────────────────────────────────
    quick = request.GET.get('quick', '')
    now = timezone.now()
    if quick == 'today':
        logs = logs.filter(timestamp__date=now.date())
    elif quick == 'week':
        logs = logs.filter(timestamp__gte=now - timedelta(days=7))
    elif quick == 'month':
        logs = logs.filter(timestamp__gte=now - timedelta(days=30))
    elif quick == 'critical':
        logs = logs.filter(level=AuditLog.LEVEL_CRITICAL)

    # ── Totals for summary cards ──────────────────────────────────────────────
    total_today    = AuditLog.objects.filter(timestamp__date=now.date()).count()
    total_warnings = AuditLog.objects.filter(
        level__in=[AuditLog.LEVEL_WARNING, AuditLog.LEVEL_CRITICAL],
        timestamp__date=now.date(),
    ).count()
    total_critical = AuditLog.objects.filter(level=AuditLog.LEVEL_CRITICAL).count()

    # ── Pagination ────────────────────────────────────────────────────────────
    paginator = Paginator(logs, 30)
    page_obj  = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj':       page_obj,
        'categories':     AuditLog.CATEGORY_CHOICES,
        'levels':         AuditLog.LEVEL_CHOICES,
        'total_today':    total_today,
        'total_warnings': total_warnings,
        'total_critical': total_critical,
        # Pass filters back for template to retain in form
        'filters': {
            'q':         search,
            'category':  category,
            'level':     level,
            'user':      username,
            'date_from': date_from,
            'date_to':   date_to,
            'quick':     quick,
        },
    }
    return render(request, 'audit/audit_log_list.html', context)


@owner_required
def audit_log_detail(request, pk):
    """Full details for a single log entry."""
    from django.shortcuts import get_object_or_404
    log = get_object_or_404(AuditLog, pk=pk)
    return render(request, 'audit/audit_log_detail.html', {'log': log})


@owner_required
def audit_export_csv(request):
    """
    Export the current filtered audit log as a CSV file.
    Re-applies the same filter logic as audit_log_list.
    """
    logs = AuditLog.objects.select_related('user').all()

    search    = request.GET.get('q', '').strip()
    category  = request.GET.get('category', '').strip()
    level     = request.GET.get('level', '').strip()
    username  = request.GET.get('user', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to   = request.GET.get('date_to', '').strip()

    if search:
        logs = logs.filter(action__icontains=search)
    if category:
        logs = logs.filter(category=category)
    if level:
        logs = logs.filter(level=level)
    if username:
        logs = logs.filter(username__icontains=username)
    if date_from:
        try:
            logs = logs.filter(timestamp__date__gte=date_from)
        except ValueError:
            pass
    if date_to:
        try:
            logs = logs.filter(timestamp__date__lte=date_to)
        except ValueError:
            pass

    # Limit export to 5000 rows to avoid memory issues
    logs = logs[:5000]

    filename = f"audit_log_{timezone.now().strftime('%Y%m%d_%H%M')}.csv"
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        'Timestamp', 'Username', 'Role', 'Level',
        'Category', 'Action', 'Object Type', 'Object ID',
        'Object', 'IP Address', 'Description',
    ])

    for log in logs:
        writer.writerow([
            log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            log.username,
            log.user_role,
            log.get_level_display(),
            log.get_category_display(),
            log.action,
            log.object_type,
            log.object_id,
            log.object_repr,
            log.ip_address or '',
            log.description,
        ])

    return response


@owner_required
def audit_clear(request):
    """
    Let the owner delete logs older than 90 days.
    POST-only with confirmation.
    """
    if request.method == 'POST':
        cutoff = timezone.now() - timedelta(days=90)
        deleted, _ = AuditLog.objects.filter(timestamp__lt=cutoff).delete()
        messages.success(request, f'{deleted:,} audit entries older than 90 days were deleted.')

        # Log the purge itself
        from .utils import log_action
        log_action(
            user=request.user,
            category=AuditLog.CATEGORY_SYSTEM,
            action=f'Purged {deleted:,} audit log entries (>90 days)',
            level=AuditLog.LEVEL_WARNING,
            request=request,
        )

    from django.shortcuts import redirect
    return redirect('audit:log_list')