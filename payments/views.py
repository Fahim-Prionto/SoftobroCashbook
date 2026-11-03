from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from accounts.models import AccountStatus
from core.decorators import super_admin_required, service_admin_required
from notifications.models import Notification, NotificationType
from payments.forms import ManualBkashPaymentForm, AdminPaymentVerificationForm, BKashSettingForm
from payments.models import Payment, PaymentStatus, BKashSetting
from subscriptions.models import Subscription, SubscriptionStatus, SubscriptionPlan
from tenants.models import AuditLog, Tenant, TenantStatus
from tenants.provisioning import provision_tenant_database


@login_required
@service_admin_required
def submit_payment_view(request):
    user = request.user
    subscription = getattr(user, 'subscription', None)

    plan_id = request.GET.get('plan')
    plan = None
    if plan_id:
        plan = SubscriptionPlan.objects.filter(id=plan_id, is_active=True).first()
    if not plan and subscription:
        plan = subscription.plan
    if not plan:
        messages.error(request, "Please choose a valid subscription plan first.")
        return redirect('subscriptions:plan_list')

    # Check for existing pending payment
    pending_payment = Payment.objects.filter(service_admin=user, status=PaymentStatus.PENDING).first()
    if pending_payment and not request.GET.get('force'):
        messages.info(request, "You already have a payment pending verification.")
        return redirect('payments:payment_pending')

    is_renewal = request.GET.get('renewal') == '1' or (
        subscription and (subscription.status == SubscriptionStatus.EXPIRED or subscription.is_currently_active)
    )

    if request.method == 'POST':
        form = ManualBkashPaymentForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                payment = form.save(commit=False)
                payment.service_admin = user
                payment.plan = plan
                payment.amount_bdt = plan.price_bdt
                payment.status = PaymentStatus.PENDING
                payment.is_renewal = is_renewal
                payment.save()

                # In-app notification
                Notification.objects.create(
                    recipient=user,
                    title="bKash Payment Submitted",
                    message=f"We received your payment submission with TrxID: {payment.bkash_transaction_id}. Our team is verifying it.",
                    notification_type=NotificationType.INFO,
                    link='/payments/pending/',
                )

                # Central audit log
                try:
                    from core.utils import get_client_ip
                    AuditLog.objects.create(
                        actor=user,
                        action=AuditLog.Action.LOGIN,
                        target=f"Payment Submitted: {payment.bkash_transaction_id}",
                        details=f"Amount: ৳{payment.amount_bdt}, Plan: {plan.name}, Renewal: {is_renewal}",
                        ip_address=get_client_ip(request),
                    )
                except Exception:
                    pass

            messages.success(request, "Payment submitted successfully! Super Admin will verify your transaction shortly.")
            return redirect('payments:payment_pending')
    else:
        form = ManualBkashPaymentForm()

    return render(request, 'payments/submit_payment.html', {
        'form': form,
        'plan': plan,
        'is_renewal': is_renewal,
    })


@login_required
@service_admin_required
def payment_pending_view(request):
    user = request.user
    pending_payment = Payment.objects.filter(service_admin=user, status=PaymentStatus.PENDING).order_by('-created_at').first()
    latest_payment = Payment.objects.filter(service_admin=user).order_by('-created_at').first()
    subscription = getattr(user, 'subscription', None)
    tenant = getattr(user, 'tenant', None)

    # If already approved and provisioned, redirect to dashboard
    if user.status == AccountStatus.ACTIVE and tenant and tenant.status == TenantStatus.PROVISIONED:
        return redirect('core:serviceadmin_dashboard')

    return render(request, 'payments/payment_pending.html', {
        'pending_payment': pending_payment,
        'latest_payment': latest_payment,
        'subscription': subscription,
        'tenant': tenant,
    })


@login_required
@service_admin_required
def payment_history_view(request):
    payments = Payment.objects.filter(service_admin=request.user).order_by('-created_at')
    return render(request, 'payments/payment_history.html', {'payments': payments})


@login_required
@super_admin_required
def admin_payment_list_view(request):
    status_filter = request.GET.get('status')
    search_query = request.GET.get('q', '').strip()

    payments = Payment.objects.select_related('service_admin', 'plan', 'approved_by').order_by('-created_at')

    if status_filter:
        payments = payments.filter(status=status_filter)

    if search_query:
        payments = payments.filter(
            service_admin__username__icontains=search_query
        ) | payments.filter(
            bkash_transaction_id__icontains=search_query
        ) | payments.filter(
            sender_bkash_number__icontains=search_query
        ) | payments.filter(
            service_admin__email__icontains=search_query
        )

    pending_count = Payment.objects.filter(status=PaymentStatus.PENDING).count()
    approved_count = Payment.objects.filter(status=PaymentStatus.APPROVED).count()
    rejected_count = Payment.objects.filter(status=PaymentStatus.REJECTED).count()

    return render(request, 'payments/admin_payment_list.html', {
        'payments': payments,
        'status_filter': status_filter,
        'search_query': search_query,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
    })


@login_required
@super_admin_required
def admin_payment_detail_view(request, payment_id):
    payment = get_object_or_404(
        Payment.objects.select_related('service_admin', 'plan', 'approved_by'),
        id=payment_id
    )
    user = payment.service_admin
    tenant = getattr(user, 'tenant', None)
    subscription = getattr(user, 'subscription', None)

    if request.method == 'POST':
        form = AdminPaymentVerificationForm(request.POST)
        if form.is_valid():
            action = form.cleaned_data['action']
            admin_notes = form.cleaned_data['admin_notes']

            if payment.status != PaymentStatus.PENDING:
                messages.warning(request, f"This payment has already been {payment.get_status_display().lower()}.")
                return redirect('payments:admin_payment_list')

            if action == 'APPROVE':
                now = timezone.now()
                payment.status = PaymentStatus.APPROVED
                payment.approval_date = now
                payment.approved_by = request.user
                payment.admin_notes = admin_notes
                payment.save()

                # Update Service Admin status to ACTIVE
                user.status = AccountStatus.ACTIVE
                user.save()

                # Update or extend subscription
                plan = payment.plan
                duration = timedelta(days=plan.duration_days)

                if subscription:
                    if subscription.is_currently_active and subscription.end_date:
                        subscription.end_date = subscription.end_date + duration
                    else:
                        subscription.start_date = now
                        subscription.end_date = now + duration
                    subscription.plan = plan
                    subscription.status = SubscriptionStatus.ACTIVE
                    subscription.save()
                else:
                    subscription = Subscription.objects.create(
                        user=user,
                        plan=plan,
                        start_date=now,
                        end_date=now + duration,
                        status=SubscriptionStatus.ACTIVE,
                    )

                # Provision isolated tenant database if not already provisioned
                if not tenant or tenant.status != TenantStatus.PROVISIONED:
                    try:
                        from core.utils import get_client_ip
                        tenant = provision_tenant_database(user, actor=request.user, ip_address=get_client_ip(request))
                    except Exception as e:
                        messages.error(request, f"Payment approved, but tenant database provisioning encountered an issue: {e}")
                        return redirect('payments:admin_payment_detail', payment_id=payment.id)

                # Audit Log
                try:
                    from core.utils import get_client_ip
                    AuditLog.objects.create(
                        actor=request.user,
                        action=AuditLog.Action.PAYMENT_APPROVE,
                        target=f"Payment #{payment.id} for {user.username}",
                        details=f"Approved TrxID: {payment.bkash_transaction_id}, Amount: ৳{payment.amount_bdt}. Plan: {plan.name}. Notes: {admin_notes}",
                        ip_address=get_client_ip(request),
                    )
                except Exception:
                    pass

                # Notification to user
                Notification.objects.create(
                    recipient=user,
                    title="Payment Approved & Account Activated!",
                    message=f"Your payment of ৳{payment.amount_bdt} for {plan.name} has been verified. Your tenant database is provisioned and ready!",
                    notification_type=NotificationType.SUCCESS,
                    link='/dashboard/',
                )

                messages.success(request, f"Payment #{payment.id} approved successfully! Tenant database has been provisioned.")
                return redirect('payments:admin_payment_list')

            elif action == 'REJECT':
                payment.status = PaymentStatus.REJECTED
                payment.approval_date = timezone.now()
                payment.approved_by = request.user
                payment.admin_notes = admin_notes
                payment.save()

                try:
                    from core.utils import get_client_ip
                    AuditLog.objects.create(
                        actor=request.user,
                        action=AuditLog.Action.PAYMENT_REJECT,
                        target=f"Payment #{payment.id} for {user.username}",
                        details=f"Rejected TrxID: {payment.bkash_transaction_id}. Reason: {admin_notes}",
                        ip_address=get_client_ip(request),
                    )
                except Exception:
                    pass

                Notification.objects.create(
                    recipient=user,
                    title="bKash Payment Rejected",
                    message=f"Your payment verification failed: {admin_notes or 'Invalid TrxID or amount mismatch'}. Please submit again.",
                    notification_type=NotificationType.DANGER,
                    link='/payments/submit/',
                )

                messages.warning(request, f"Payment #{payment.id} has been marked as REJECTED.")
                return redirect('payments:admin_payment_list')
    else:
        form = AdminPaymentVerificationForm()

    return render(request, 'payments/admin_payment_detail.html', {
        'payment': payment,
        'form': form,
        'user': user,
        'tenant': tenant,
        'subscription': subscription,
    })


@login_required
@super_admin_required
def admin_bkash_settings_view(request):
    bkash_setting = BKashSetting.get_settings()

    if request.method == 'POST':
        form = BKashSettingForm(request.POST, instance=bkash_setting)
        if form.is_valid():
            setting_obj = form.save(commit=False)
            setting_obj.updated_by = request.user
            setting_obj.save()

            try:
                from core.utils import get_client_ip
                AuditLog.objects.create(
                    actor=request.user,
                    action='SETTINGS_UPDATE',
                    target=f"bKash Number: {setting_obj.company_number}",
                    details=f"Updated bKash payment number to {setting_obj.company_number} ({setting_obj.account_type})",
                    ip_address=get_client_ip(request),
                )
            except Exception:
                pass

            messages.success(
                request,
                f"bKash receiving configuration updated! Official number '{setting_obj.company_number}' ({setting_obj.account_type}) is now active across all customer payment and landing pages."
            )
            return redirect('payments:admin_payment_list')
    else:
        form = BKashSettingForm(instance=bkash_setting)

    return render(request, 'payments/admin_bkash_settings.html', {
        'form': form,
        'bkash_setting': bkash_setting,
    })

