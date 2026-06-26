from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse


# ─── Owner Required ───────────────────────────────────────────────────────────

def owner_required(view_func):
    """
    Restricts view to owner role only.
    Attendants get redirected with an error message.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to continue.')
            return redirect('login')

        if not request.user.is_owner:
            messages.error(request, 'Access denied. This area is for the owner only.')
            return redirect('dashboard')

        return view_func(request, *args, **kwargs)
    return wrapper


# ─── Attendant Required ───────────────────────────────────────────────────────

def attendant_required(view_func):
    """
    Restricts view to authenticated staff only (owner or attendant).
    Blocks unauthenticated users.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to continue.')
            return redirect('login')

        if not request.user.is_active:
            messages.error(request, 'Your account has been deactivated. Contact the owner.')
            return redirect('login')

        return view_func(request, *args, **kwargs)
    return wrapper


# ─── PIN Required ─────────────────────────────────────────────────────────────

def pin_required(action_name='this action'):
    """
    Decorator factory that marks a view as requiring owner PIN.
    The actual PIN check happens via AJAX (pin_verify endpoint).
    This decorator adds context so the template knows to show the PIN modal.

    Usage:
        @pin_required('apply discount')
        def apply_discount(request): ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.error(request, 'Please log in to continue.')
                return redirect('login')

            # If owner is doing it themselves, no PIN needed
            if request.user.is_owner:
                return view_func(request, *args, **kwargs)

            # For AJAX requests, return JSON error
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                pin_verified = request.session.get(f'pin_verified_{action_name}', False)
                if not pin_verified:
                    return JsonResponse({
                        'success': False,
                        'requires_pin': True,
                        'action': action_name,
                        'message': f'Owner PIN required to {action_name}.'
                    }, status=403)

            # For regular requests, check session flag
            pin_verified = request.session.get(f'pin_verified_{action_name}', False)
            if not pin_verified:
                messages.warning(request, f'Owner PIN is required to {action_name}.')
                return redirect('dashboard')

            # Clear the flag after use
            del request.session[f'pin_verified_{action_name}']
            return view_func(request, *args, **kwargs)

        wrapper.requires_pin = True
        wrapper.pin_action = action_name
        return wrapper
    return decorator


# ─── Active User Required ─────────────────────────────────────────────────────

def active_required(view_func):
    """
    Ensures the logged-in user's account is still active.
    Useful for views that don't use login_required but need active check.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        if not request.user.is_active:
            messages.error(request, 'Your account is inactive. Please contact the owner.')
            from django.contrib.auth import logout
            logout(request)
            return redirect('login')

        return view_func(request, *args, **kwargs)
    return wrapper


# ─── AJAX Required ────────────────────────────────────────────────────────────

def ajax_required(view_func):
    """
    Ensures the request is an AJAX request.
    Returns 400 Bad Request for non-AJAX calls.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
            return JsonResponse({'error': 'AJAX request required.'}, status=400)
        return view_func(request, *args, **kwargs)
    return wrapper