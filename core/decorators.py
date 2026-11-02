from functools import wraps
from django.contrib import messages
from django.shortcuts import redirect
from accounts.models import AccountStatus
from tenants.models import TenantStatus


def super_admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not request.user.is_super_admin:
            messages.error(request, "Access restricted to Super Administrators only.")
            return redirect('core:landing')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def service_admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not request.user.is_service_admin:
            messages.error(request, "Access restricted to Business Service Admins.")
            return redirect('core:superadmin_dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def approved_service_admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        if not request.user.is_service_admin:
            return redirect('core:superadmin_dashboard')

        # Check account status
        if request.user.status == AccountStatus.PENDING_APPROVAL:
            messages.info(request, "Your account is pending Super Admin payment verification.")
            return redirect('payments:payment_pending')
        elif request.user.status in [AccountStatus.SUSPENDED, AccountStatus.DEACTIVATED]:
            messages.error(request, "Your account has been suspended or deactivated. Please contact support.")
            return redirect('core:landing')

        # Check tenant database status
        tenant = getattr(request.user, 'tenant', None)
        if not tenant or tenant.status != TenantStatus.PROVISIONED:
            messages.warning(request, "Your isolated database is being set up. Please wait or check your payment status.")
            return redirect('payments:payment_pending')

        # Check subscription status
        subscription = getattr(request.user, 'subscription', None)
        if subscription and not subscription.is_currently_active and not subscription.is_in_grace_period:
            messages.warning(request, "Your subscription has expired. Please renew your plan to continue creating and editing.")
            # Still allow viewing read-only, but restrict if needed. We will direct them to my_subscription if needed.

        return view_func(request, *args, **kwargs)
    return _wrapped_view

