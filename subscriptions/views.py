from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from core.decorators import super_admin_required, service_admin_required
from subscriptions.forms import SubscriptionPlanForm
from subscriptions.models import SubscriptionPlan, Subscription, SubscriptionStatus


def plan_list_view(request):
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price_bdt')
    return render(request, 'subscriptions/plan_list.html', {'plans': plans})


@login_required
@service_admin_required
def my_subscription_view(request):
    subscription = getattr(request.user, 'subscription', None)
    tenant = getattr(request.user, 'tenant', None)

    # Count current businesses and cashbooks
    from businesses.models import Business
    from cashbooks.models import Cashbook
    from transactions.models import Transaction

    business_count = 0
    cashbook_count = 0
    transaction_count = 0

    if tenant and tenant.status == 'PROVISIONED':
        try:
            business_count = Business.objects.count()
            cashbook_count = Cashbook.objects.count()
            transaction_count = Transaction.objects.count()
        except Exception:
            pass

    return render(request, 'subscriptions/my_subscription.html', {
        'subscription': subscription,
        'business_count': business_count,
        'cashbook_count': cashbook_count,
        'transaction_count': transaction_count,
    })


@login_required
@service_admin_required
def renew_view(request):
    subscription = getattr(request.user, 'subscription', None)
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price_bdt')
    return render(request, 'subscriptions/renew.html', {
        'subscription': subscription,
        'plans': plans,
    })


@login_required
@super_admin_required
def admin_plan_list_view(request):
    plans = SubscriptionPlan.objects.all().order_by('price_bdt')
    return render(request, 'subscriptions/admin_plan_list.html', {'plans': plans})


@login_required
@super_admin_required
def admin_plan_create_view(request):
    if request.method == 'POST':
        form = SubscriptionPlanForm(request.POST)
        if form.is_valid():
            plan = form.save()
            messages.success(request, f"Plan '{plan.name}' created successfully.")
            return redirect('subscriptions:admin_plan_list')
    else:
        form = SubscriptionPlanForm()

    return render(request, 'subscriptions/admin_plan_form.html', {'form': form, 'title': 'Create Subscription Plan'})


@login_required
@super_admin_required
def admin_plan_edit_view(request, plan_id):
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)
    if request.method == 'POST':
        form = SubscriptionPlanForm(request.POST, instance=plan)
        if form.is_valid():
            form.save()
            messages.success(request, f"Plan '{plan.name}' updated successfully.")
            return redirect('subscriptions:admin_plan_list')
    else:
        form = SubscriptionPlanForm(instance=plan)

    return render(request, 'subscriptions/admin_plan_form.html', {'form': form, 'plan': plan, 'title': f'Edit {plan.name}'})


@login_required
@super_admin_required
def admin_plan_toggle_view(request, plan_id):
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)
    plan.is_active = not plan.is_active
    plan.save()
    status_str = "activated" if plan.is_active else "deactivated"
    messages.info(request, f"Plan '{plan.name}' has been {status_str}.")
    return redirect('subscriptions:admin_plan_list')


@login_required
@super_admin_required
def admin_plan_delete_view(request, plan_id):
    plan = get_object_or_404(SubscriptionPlan, id=plan_id)
    if plan.user_subscriptions.exists():
        messages.error(request, f"Cannot delete '{plan.name}' because users are currently subscribed to it. You can deactivate it instead.")
    else:
        plan.delete()
        messages.success(request, f"Plan '{plan.name}' deleted successfully.")
    return redirect('subscriptions:admin_plan_list')
