from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password, check_password
from django.db.models import F, Sum, ExpressionWrapper, DecimalField, Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import User, ShopProfile, OwnerPIN, FailedPINAttempt, UserSession
from .forms import (
    LoginForm, RegisterShopForm, CreateUserForm,
    EditUserForm, ChangePINForm, ChangePasswordForm,
)
from .decorators import owner_required
from audit.utils import log_action


# ─── Login ────────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = LoginForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password'],
        )
        if user:
            if not user.is_active:
                messages.error(request, 'Your account has been deactivated. Contact the owner.')
                return render(request, 'accounts/login.html', {'form': form})

            login(request, user)
            UserSession.objects.update_or_create(
                user=user,
                defaults={
                    'session_key':   request.session.session_key or '',
                    'last_activity': timezone.now(),
                    'ip_address':    get_client_ip(request),
                    'device':        request.META.get('HTTP_USER_AGENT', '')[:200],
                }
            )
            log_action(user, 'LOGIN', 'User', user.id, f'{user.full_name} logged in')
            messages.success(request, f'Welcome back, {user.full_name}!')
            return redirect(request.GET.get('next', 'dashboard'))
        else:
            messages.error(request, 'Invalid username or password.')

    return render(request, 'accounts/login.html', {'form': form})


# ─── Logout ───────────────────────────────────────────────────────────────────

@login_required
def logout_view(request):
    log_action(request.user, 'LOGOUT', 'User', request.user.id,
               f'{request.user.full_name} logged out')
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


# ─── Register Shop ────────────────────────────────────────────────────────────

def register_shop(request):
    if User.objects.filter(role='owner').exists():
        messages.error(request, 'Shop is already set up. Please log in.')
        return redirect('login')

    form = RegisterShopForm(request.POST or None, request.FILES or None)

    if request.method == 'POST' and form.is_valid():
        user = User.objects.create_user(
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password'],
            full_name=form.cleaned_data['full_name'],
            phone=form.cleaned_data.get('phone', ''),
            role='owner',
            is_staff=True,
        )
        ShopProfile.objects.create(
            owner=user,
            name=form.cleaned_data['shop_name'],
            address=form.cleaned_data.get('address', ''),
            phone=form.cleaned_data.get('shop_phone', ''),
            whatsapp=form.cleaned_data.get('whatsapp', ''),
            email=form.cleaned_data.get('email', ''),
            logo=request.FILES.get('logo'),
        )
        OwnerPIN.objects.create(
            user=user,
            pin_hash=make_password(form.cleaned_data.get('pin', '0000')),
        )
        login(request, user)
        messages.success(request, f'Welcome to {form.cleaned_data["shop_name"]}!')
        return redirect('dashboard')

    return render(request, 'accounts/register_shop.html', {'form': form})


# ─── PIN Verify ───────────────────────────────────────────────────────────────

@login_required
@require_POST
def pin_verify(request):
    entered_pin = request.POST.get('pin', '').strip()
    action      = request.POST.get('action', 'unknown')

    try:
        owner     = User.objects.get(role='owner')
        owner_pin = owner.pin
    except (User.DoesNotExist, OwnerPIN.DoesNotExist):
        return JsonResponse({'success': False, 'message': 'Owner PIN not configured.'})

    if owner_pin.is_locked:
        remaining = (owner_pin.locked_until - timezone.now()).seconds // 60
        return JsonResponse({'success': False,
                             'message': f'PIN locked. Try again in {remaining} minutes.'})

    if check_password(entered_pin, owner_pin.pin_hash):
        owner_pin.reset_attempts()
        log_action(request.user, 'PIN_VERIFIED', 'OwnerPIN', owner.id,
                   f'PIN verified for: {action}')
        return JsonResponse({'success': True, 'message': 'PIN verified.'})

    owner_pin.increment_attempts()
    FailedPINAttempt.objects.create(
        user=request.user,
        action_attempted=action,
        ip_address=get_client_ip(request),
    )
    attempts_left = max(0, 3 - owner_pin.attempts)
    msg = ('Too many failed attempts. PIN locked for 30 minutes.'
           if owner_pin.is_locked else
           f'Wrong PIN. {attempts_left} attempt(s) remaining.')
    log_action(request.user, 'PIN_FAILED', 'OwnerPIN', owner.id, f'Failed PIN for: {action}')
    return JsonResponse({'success': False, 'message': msg})


# ─── User Management ──────────────────────────────────────────────────────────

@login_required
@owner_required
def user_list(request):
    users = User.objects.all().order_by('role', 'full_name')
    return render(request, 'accounts/user_list.html', {'users': users})


@login_required
@owner_required
def user_create(request):
    form = CreateUserForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = User.objects.create_user(
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password'],
            full_name=form.cleaned_data['full_name'],
            phone=form.cleaned_data.get('phone', ''),
            role=form.cleaned_data['role'],
        )
        log_action(request.user, 'CREATE', 'User', user.id,
                   f'Created user: {user.full_name}')
        messages.success(request, f'{user.full_name} created successfully.')
        return redirect('user_list')

    return render(request, 'accounts/user_form.html', {
        'form':  form,
        'title': 'Add Attendant',
    })


@login_required
@owner_required
def user_edit(request, user_id):
    target = get_object_or_404(User, id=user_id)

    # Prevent editing another owner
    if target.is_owner and target != request.user:
        messages.error(request, 'You cannot edit another owner account.')
        return redirect('user_list')

    form = EditUserForm(request.POST or None, instance=target)

    if request.method == 'POST' and form.is_valid():
        form.save()
        log_action(request.user, 'UPDATE', 'User', target.id,
                   f'Edited user: {target.full_name}')
        messages.success(request, f'{target.full_name} updated successfully.')
        return redirect('user_list')

    return render(request, 'accounts/user_form.html', {
        'form':  form,
        'title': 'Edit Attendant',
        'target': target,
    })


@login_required
@owner_required
def user_toggle_active(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user.is_owner:
        messages.error(request, 'Cannot deactivate the owner account.')
        return redirect('user_list')
    user.is_active = not user.is_active
    user.save()
    status = 'activated' if user.is_active else 'deactivated'
    log_action(request.user, 'UPDATE', 'User', user.id, f'User {status}: {user.full_name}')
    messages.success(request, f'{user.full_name} has been {status}.')
    return redirect('user_list')


# ─── Force Logout ─────────────────────────────────────────────────────────────

@login_required
@owner_required
@require_POST
def force_logout(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user.is_owner:
        return JsonResponse({'success': False, 'message': 'Cannot force logout the owner.'})
    UserSession.objects.filter(user=user).update(
        last_activity=timezone.now() - timedelta(hours=1)
    )
    log_action(request.user, 'FORCE_LOGOUT', 'User', user.id,
               f'Force logged out: {user.full_name}')
    return JsonResponse({'success': True,
                         'message': f'{user.full_name} has been logged out.'})


# ─── Dark Mode ────────────────────────────────────────────────────────────────

@login_required
@require_POST
def toggle_dark_mode(request):
    request.user.dark_mode = not request.user.dark_mode
    request.user.save(update_fields=['dark_mode'])
    return JsonResponse({'dark_mode': request.user.dark_mode})


# ─── Change PIN ───────────────────────────────────────────────────────────────

@login_required
@owner_required
def change_pin(request):
    form = ChangePINForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        try:
            owner_pin = request.user.pin
        except OwnerPIN.DoesNotExist:
            owner_pin = OwnerPIN(user=request.user)

        if not check_password(form.cleaned_data['old_pin'], owner_pin.pin_hash):
            messages.error(request, 'Current PIN is incorrect.')
            return render(request, 'accounts/change_pin.html', {'form': form})

        owner_pin.pin_hash = make_password(form.cleaned_data['new_pin'])
        owner_pin.reset_attempts()
        owner_pin.save()
        log_action(request.user, 'UPDATE', 'OwnerPIN', owner_pin.id, 'Owner PIN changed')
        messages.success(request, 'PIN changed successfully.')
        return redirect('profile')

    return render(request, 'accounts/change_pin.html', {'form': form})


# ─── Change Password ──────────────────────────────────────────────────────────

@login_required
def change_password(request):
    form = ChangePasswordForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        if not request.user.check_password(form.cleaned_data['old_password']):
            messages.error(request, 'Current password is incorrect.')
            return render(request, 'accounts/change_password.html', {'form': form})

        request.user.set_password(form.cleaned_data['new_password'])
        request.user.save()
        # Keep the user logged in after password change
        update_session_auth_hash(request, request.user)
        log_action(request.user, 'UPDATE', 'User', request.user.id, 'Password changed')
        messages.success(request, 'Password changed successfully.')
        return redirect('profile')

    return render(request, 'accounts/change_password.html', {'form': form})


# ─── Profile ──────────────────────────────────────────────────────────────────

@login_required
def profile(request):
    # Safely count related objects — gracefully handles missing related_names
    sales_count = 0
    products_count = 0
    customers_count = 0

    try:
        sales_count = request.user.sales.count()
    except Exception:
        pass
    try:
        products_count = request.user.products_created.count()
    except Exception:
        pass
    try:
        customers_count = request.user.customers_created.count()
    except Exception:
        pass

    return render(request, 'accounts/profile.html', {
        'user':            request.user,
        'sales_count':     sales_count,
        'products_count':  products_count,
        'customers_count': customers_count,
    })


# ─── Users Online (AJAX) ──────────────────────────────────────────────────────

@login_required
@owner_required
def users_online(request):
    from django.conf import settings
    timeout  = getattr(settings, 'USER_ONLINE_TIMEOUT', 5)
    cutoff   = timezone.now() - timedelta(minutes=timeout)
    sessions = UserSession.objects.filter(
        last_activity__gte=cutoff
    ).select_related('user')
    data = [
        {
            'name':          s.user.full_name,
            'role':          s.user.get_role_display(),
            'last_activity': s.last_activity.strftime('%H:%M'),
            'user_id':       s.user.id,
        }
        for s in sessions
    ]
    return JsonResponse({'users': data, 'count': len(data)})


# ─── Helpers ──────────────────────────────────────────────────────────────────

def get_client_ip(request):
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


# ─── Dashboard ────────────────────────────────────────────────────────────────

# ─── Dashboard ────────────────────────────────────────────────────────────────
# Replace your existing dashboard() function in accounts/views.py with this.

@login_required
def dashboard(request):
    from sales.models import Sale, SaleItem
    from products.models import Product
    from customers.models import Customer
    from discounts.models import Discount
    from django.conf import settings

    today = date.today()

    date_from = request.GET.get('date_from', today.isoformat())
    date_to   = request.GET.get('date_to',   today.isoformat())

    try:
        start = date.fromisoformat(date_from)
        end   = date.fromisoformat(date_to)
    except ValueError:
        start = end = today
        date_from = date_to = today.isoformat()

    # ── Base queryset for the selected date range ──────────────────────────────
    qs = Sale.objects.filter(
        created_at__date__gte=start,
        created_at__date__lte=end,
    )

    # ── Attendant-only: their own sales today ─────────────────────────────────
    my_sales_today      = 0
    my_transactions     = 0
    my_recent_sales     = []

    if request.user.is_attendant:
        my_qs = qs.filter(attendant=request.user)
        my_sales_today  = my_qs.aggregate(t=Sum('total'))['t'] or 0
        my_transactions = my_qs.count()
        my_recent_sales = (
            my_qs
            .select_related('customer')
            .order_by('-created_at')[:10]
        )

    # ── Owner-only data ───────────────────────────────────────────────────────
    total_sales        = 0
    total_transactions = 0
    gross_profit       = 0
    cash_sales         = 0
    momo_sales         = 0
    credit_sales       = 0
    split_sales        = 0
    recent_sales       = []
    top_products       = []
    active_discounts   = []
    overdue_debts      = []
    users_online       = 0

    if request.user.is_owner:
        total_sales        = qs.aggregate(t=Sum('total'))['t'] or 0
        total_transactions = qs.count()

        cash_sales   = qs.filter(payment_method='cash').aggregate(t=Sum('total'))['t'] or 0
        momo_sales   = qs.filter(payment_method='momo').aggregate(t=Sum('total'))['t'] or 0
        credit_sales = qs.filter(payment_method='credit').aggregate(t=Sum('total'))['t'] or 0
        split_sales  = qs.filter(payment_method='split').aggregate(t=Sum('total'))['t'] or 0

        gross_profit = (
            SaleItem.objects
            .filter(sale__created_at__date__gte=start,
                    sale__created_at__date__lte=end)
            .aggregate(gp=Sum(
                ExpressionWrapper(
                    (F('unit_price') - F('cost_price')) * F('quantity'),
                    output_field=DecimalField(),
                )
            ))['gp'] or 0
        )

        recent_sales = (
            Sale.objects
            .select_related('attendant', 'customer')
            .order_by('-created_at')[:10]
        )

        top_products = (
            SaleItem.objects
            .filter(sale__created_at__date__gte=start,
                    sale__created_at__date__lte=end)
            .values(name=F('product_name'))
            .annotate(total_sold=Sum('quantity'))
            .order_by('-total_sold')[:5]
        )

        try:
            active_discounts = Discount.objects.filter(
                Q(expiry_date__gte=today) | Q(expiry_date__isnull=True),
                is_active=True,
            )[:5]
        except Exception:
            active_discounts = []

        try:
            for c in Customer.objects.filter(credit_balance__gt=0):
                last_sale = c.sales.filter(
                    payment_method='credit'
                ).order_by('-created_at').first()
                ref_date = last_sale.created_at.date() if last_sale else c.created_at.date()
                c.days_overdue = (today - ref_date).days
                overdue_debts.append(c)
            overdue_debts.sort(key=lambda c: c.days_overdue, reverse=True)
        except Exception:
            overdue_debts = []

        try:
            timeout      = getattr(settings, 'USER_ONLINE_TIMEOUT', 5)
            cutoff       = timezone.now() - timedelta(minutes=timeout)
            users_online = UserSession.objects.filter(last_activity__gte=cutoff).count()
        except Exception:
            users_online = 0

    # ── Shared: low stock (both roles need this) ───────────────────────────────
    low_stock = []
    for p in Product.objects.select_related('stock_level').filter(is_active=True):
        try:
            qty     = p.stock_level.quantity
            reorder = p.stock_level.reorder_point
            if qty <= reorder:
                low_stock.append({
                    'name':          p.name,
                    'current_stock': qty,
                    'reorder_point': reorder,
                })
        except Exception:
            pass

    # ── Shared: customer count (safe for both roles) ───────────────────────────
    total_customers = Customer.objects.count()

    try:
        shop     = ShopProfile.objects.first()
        currency = shop.currency_symbol if shop else 'GH₵'
    except Exception:
        shop     = None
        currency = 'GH₵'

    return render(request, 'dashboard.html', {
        'shop':               shop,
        'currency':           currency,
        'date_from':          date_from,
        'date_to':            date_to,

        # Owner-only
        'total_sales':        f'{total_sales:,.2f}',
        'total_transactions': total_transactions,
        'gross_profit':       f'{gross_profit:,.2f}',
        'cash_sales':         f'{cash_sales:,.2f}',
        'momo_sales':         f'{momo_sales:,.2f}',
        'credit_sales':       f'{credit_sales:,.2f}',
        'split_sales':        f'{split_sales:,.2f}',
        'recent_sales':       recent_sales,
        'top_products':       top_products,
        'active_discounts':   active_discounts,
        'overdue_debts':      overdue_debts,
        'users_online':       users_online,

        # Attendant-only
        'my_sales_today':     f'{my_sales_today:,.2f}',
        'my_transactions':    my_transactions,
        'my_recent_sales':    my_recent_sales,

        # Shared
        'total_customers':    total_customers,
        'low_stock':          low_stock,
    })