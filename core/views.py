from decimal import Decimal
from datetime import timedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from accounts.models import User, UserRole, AccountStatus
from core.decorators import super_admin_required, approved_service_admin_required
from payments.models import Payment, PaymentStatus
from subscriptions.models import Subscription, SubscriptionStatus, SubscriptionPlan
from tenants.models import Tenant, TenantStatus, AuditLog
from tenants.provisioning import delete_tenant_database


import logging

logger = logging.getLogger(__name__)


def landing_view(request):
    if request.user.is_authenticated:
        return redirect('core:dashboard_redirect')
    try:
        plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price_bdt')
    except Exception:
        plans = []
    return render(request, 'core/landing.html', {'plans': plans})


def about_view(request):
    return render(request, 'core/about.html')


def features_view(request):
    return render(request, 'core/features.html')


def pricing_view(request):
    try:
        plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price_bdt')
    except Exception:
        plans = []
    return render(request, 'core/pricing.html', {'plans': plans})


def how_it_works_view(request):
    return render(request, 'core/how_it_works.html')


def contact_view(request):
    if request.method == 'POST':
        messages.success(request, "Thank you! Your message has been received. Our team will contact you shortly.")
        return redirect('core:contact')
    return render(request, 'core/contact.html')


@login_required
def dashboard_redirect(request):
    user = request.user
    if user.is_super_admin:
        return redirect('core:superadmin_dashboard')
    elif user.is_service_admin:
        if user.status == AccountStatus.PENDING_APPROVAL:
            return redirect('payments:payment_pending')
        elif user.status in [AccountStatus.SUSPENDED, AccountStatus.DEACTIVATED]:
            messages.error(request, "Your account is not active. Please contact customer support.")
            return redirect('accounts:logout')
        return redirect('core:serviceadmin_dashboard')
    return redirect('core:landing')


@login_required
@super_admin_required
def superadmin_dashboard_view(request):
    try:
        total_service_admins = User.objects.filter(role=UserRole.SERVICE_ADMIN).count()
        pending_approvals = User.objects.filter(role=UserRole.SERVICE_ADMIN, status=AccountStatus.PENDING_APPROVAL).count()
        active_subscriptions = Subscription.objects.filter(status=SubscriptionStatus.ACTIVE).count()
        expired_subscriptions = Subscription.objects.filter(status=SubscriptionStatus.EXPIRED).count()
        suspended_accounts = User.objects.filter(status=AccountStatus.SUSPENDED).count()

        total_revenue = Payment.objects.filter(status=PaymentStatus.APPROVED).aggregate(
            total=Sum('amount_bdt')
        )['total'] or Decimal('0.00')

        pending_payments = Payment.objects.filter(status=PaymentStatus.PENDING).count()
        total_tenants = Tenant.objects.count()

        recent_users = User.objects.filter(role=UserRole.SERVICE_ADMIN).select_related('subscription__plan', 'tenant').order_by('-date_joined')[:8]
        recent_payments = Payment.objects.select_related('service_admin', 'plan').order_by('-created_at')[:8]
    except Exception as e:
        logger.error(f"Error in superadmin_dashboard_view stats: {e}", exc_info=True)
        total_service_admins = pending_approvals = active_subscriptions = expired_subscriptions = suspended_accounts = 0
        total_revenue = Decimal('0.00')
        pending_payments = total_tenants = 0
        recent_users = []
        recent_payments = []

    return render(request, 'core/superadmin_dashboard.html', {
        'total_service_admins': total_service_admins,
        'pending_approvals': pending_approvals,
        'active_subscriptions': active_subscriptions,
        'expired_subscriptions': expired_subscriptions,
        'suspended_accounts': suspended_accounts,
        'total_revenue': total_revenue,
        'pending_payments': pending_payments,
        'total_tenants': total_tenants,
        'recent_users': recent_users,
        'recent_payments': recent_payments,
    })


@login_required
@super_admin_required
def admin_service_admin_list_view(request):
    search_q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status')
    plan_filter = request.GET.get('plan')

    admins = User.objects.filter(role=UserRole.SERVICE_ADMIN).select_related(
        'subscription__plan', 'tenant'
    ).order_by('-date_joined')

    if status_filter:
        admins = admins.filter(status=status_filter)
    if plan_filter:
        admins = admins.filter(subscription__plan_id=plan_filter)
    if search_q:
        admins = admins.filter(
            Q(username__icontains=search_q) |
            Q(business_name__icontains=search_q) |
            Q(email__icontains=search_q) |
            Q(phone_number__icontains=search_q) |
            Q(first_name__icontains=search_q) |
            Q(last_name__icontains=search_q)
        )

    plans = SubscriptionPlan.objects.all()

    return render(request, 'core/admin_service_admin_list.html', {
        'admins': admins,
        'plans': plans,
        'search_q': search_q,
        'status_filter': status_filter,
        'plan_filter': plan_filter,
    })


@login_required
@super_admin_required
def admin_service_admin_detail_view(request, user_id):
    admin_user = get_object_or_404(
        User.objects.select_related('subscription__plan', 'tenant'),
        id=user_id,
        role=UserRole.SERVICE_ADMIN
    )
    payments = admin_user.payments.all().order_by('-created_at')
    tenant = getattr(admin_user, 'tenant', None)
    subscription = getattr(admin_user, 'subscription', None)

    return render(request, 'core/admin_service_admin_detail.html', {
        'admin_user': admin_user,
        'payments': payments,
        'tenant': tenant,
        'subscription': subscription,
    })


@login_required
@super_admin_required
def admin_service_admin_status_view(request, user_id):
    admin_user = get_object_or_404(User, id=user_id, role=UserRole.SERVICE_ADMIN)
    new_status = request.POST.get('status')

    if new_status in AccountStatus.values:
        old_status = admin_user.status
        admin_user.status = new_status
        admin_user.save()

        # If activated / approved, automatically provision tenant database if not already provisioned
        if new_status == AccountStatus.ACTIVE:
            tenant = getattr(admin_user, 'tenant', None)
            if not tenant or tenant.status != TenantStatus.PROVISIONED:
                try:
                    from tenants.provisioning import provision_tenant_database
                    from core.utils import get_client_ip
                    provision_tenant_database(admin_user, actor=request.user, ip_address=get_client_ip(request))
                    messages.success(request, f"Tenant database for '{admin_user.username}' was automatically created & provisioned.")
                except Exception as e:
                    logger.error(f"Auto-provisioning failed for {admin_user.username}: {e}", exc_info=True)
                    messages.warning(request, f"Account activated, but tenant database provisioning encountered an issue: {e}")

        try:
            from core.utils import get_client_ip
            AuditLog.objects.create(
                actor=request.user,
                action=AuditLog.Action.USER_STATUS_CHANGE,
                target=f"User: {admin_user.username}",
                details=f"Status changed from {old_status} to {new_status}",
                ip_address=get_client_ip(request),
            )
        except Exception:
            pass
        messages.success(request, f"Status of '{admin_user.username}' changed to {admin_user.get_status_display()}.")

    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url:
        return redirect(next_url)
    return redirect('core:admin_service_admin_detail', user_id=admin_user.id)


@login_required
@super_admin_required
def admin_service_admin_delete_view(request, user_id):
    admin_user = get_object_or_404(
        User.objects.select_related('tenant'),
        id=user_id,
        role=UserRole.SERVICE_ADMIN
    )
    tenant = getattr(admin_user, 'tenant', None)

    if request.method == 'POST':
        # Safely delete tenant database first
        if tenant:
            try:
                from core.utils import get_client_ip
                delete_tenant_database(
                    tenant,
                    actor=request.user,
                    ip_address=get_client_ip(request),
                )
            except Exception as e:
                logger.warning(f"Error dropping tenant database {tenant.db_name}: {e}")
                try:
                    tenant.delete()
                except Exception:
                    pass

        # Audit Log
        try:
            from core.utils import get_client_ip
            AuditLog.objects.create(
                actor=request.user,
                action=AuditLog.Action.USER_STATUS_CHANGE,
                target=f"Deleted Service Admin: {admin_user.username}",
                details=f"Email: {admin_user.email}, Business: {admin_user.business_name}",
                ip_address=get_client_ip(request),
            )
        except Exception:
            pass

        username = admin_user.username
        admin_user.delete()
        messages.success(request, f"Service Admin '{username}' and their isolated tenant database have been automatically deleted.")
        return redirect('core:admin_service_admin_list')

    return render(request, 'core/admin_delete_user_confirm.html', {
        'admin_user': admin_user,
        'tenant': tenant,
    })


@login_required
@approved_service_admin_required
def serviceadmin_dashboard_view(request):
    from businesses.models import Business
    from cashbooks.models import Cashbook
    from transactions.models import Transaction, TransactionType

    businesses = Business.objects.all()
    cashbooks = Cashbook.objects.select_related('business').all()

    total_businesses = businesses.count()
    total_cashbooks = cashbooks.count()

    # Financial sums
    total_cash_in = Transaction.objects.filter(
        transaction_type=TransactionType.CASH_IN
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')

    total_cash_out = Transaction.objects.filter(
        transaction_type=TransactionType.CASH_OUT
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')

    total_opening = sum((b.opening_balance for b in businesses), Decimal('0.00')) + sum((cb.opening_balance for cb in cashbooks), Decimal('0.00'))
    current_net_balance = total_opening + total_cash_in - total_cash_out

    # Recent transactions
    recent_transactions = Transaction.objects.select_related('cashbook__business').order_by('-date', '-created_at')[:8]

    # Chart data for last 6 months
    today = timezone.now().date()
    months_labels = []
    cash_in_data = []
    cash_out_data = []

    for i in range(5, -1, -1):
        # approximate month calculation
        m_date = today - timedelta(days=i * 30)
        m_start = m_date.replace(day=1)
        next_month = (m_start + timedelta(days=32)).replace(day=1)

        m_in = Transaction.objects.filter(
            date__gte=m_start,
            date__lt=next_month,
            transaction_type=TransactionType.CASH_IN
        ).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')

        m_out = Transaction.objects.filter(
            date__gte=m_start,
            date__lt=next_month,
            transaction_type=TransactionType.CASH_OUT
        ).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')

        months_labels.append(m_start.strftime('%b %Y'))
        cash_in_data.append(float(m_in))
        cash_out_data.append(float(m_out))

    subscription = getattr(request.user, 'subscription', None)

    return render(request, 'core/serviceadmin_dashboard.html', {
        'total_businesses': total_businesses,
        'total_cashbooks': total_cashbooks,
        'total_cash_in': total_cash_in,
        'total_cash_out': total_cash_out,
        'current_net_balance': current_net_balance,
        'recent_transactions': recent_transactions,
        'subscription': subscription,
        'months_labels': months_labels,
        'cash_in_data': cash_in_data,
        'cash_out_data': cash_out_data,
    })
