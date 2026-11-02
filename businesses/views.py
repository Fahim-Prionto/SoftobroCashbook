from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from businesses.forms import BusinessForm
from businesses.models import Business
from core.decorators import approved_service_admin_required


@login_required
@approved_service_admin_required
def business_list_view(request):
    businesses = Business.objects.prefetch_related('cashbooks').all()

    subscription = getattr(request.user, 'subscription', None)
    can_add = True
    max_allowed = 1
    if subscription:
        max_allowed = subscription.plan.max_businesses
        if businesses.count() >= max_allowed:
            can_add = False

    business_data = []
    for b in businesses:
        business_data.append({
            'obj': b,
            'cashbooks_count': b.cashbooks.count(),
            'total_in': b.get_total_cash_in(),
            'total_out': b.get_total_cash_out(),
            'balance': b.get_current_balance(),
        })

    return render(request, 'businesses/business_list.html', {
        'businesses': business_data,
        'can_add': can_add,
        'current_count': businesses.count(),
        'max_allowed': max_allowed,
    })


@login_required
@approved_service_admin_required
def business_create_view(request):
    subscription = getattr(request.user, 'subscription', None)
    current_count = Business.objects.count()

    if subscription and not subscription.can_create_business(current_count):
        messages.error(request, f"You have reached your limit of {subscription.plan.max_businesses} business(es). Please upgrade your subscription.")
        return redirect('businesses:business_list')

    if request.method == 'POST':
        form = BusinessForm(request.POST)
        if form.is_valid():
            biz = form.save()
            messages.success(request, f"Business '{biz.name}' created successfully.")
            return redirect('businesses:business_detail', business_id=biz.id)
    else:
        form = BusinessForm()

    return render(request, 'businesses/business_form.html', {
        'form': form,
        'title': 'Add New Business',
    })


@login_required
@approved_service_admin_required
def business_detail_view(request, business_id):
    biz = get_object_or_404(Business, id=business_id)
    cashbooks = biz.cashbooks.all()

    subscription = getattr(request.user, 'subscription', None)
    can_add_cashbook = True
    max_cashbooks = 3
    if subscription:
        max_cashbooks = subscription.plan.max_cashbooks_per_business
        if cashbooks.count() >= max_cashbooks:
            can_add_cashbook = False

    from transactions.models import Transaction
    recent_transactions = Transaction.objects.filter(cashbook__business=biz).order_by('-date', '-created_at')[:10]

    return render(request, 'businesses/business_detail.html', {
        'business': biz,
        'cashbooks': cashbooks,
        'can_add_cashbook': can_add_cashbook,
        'max_cashbooks': max_cashbooks,
        'total_in': biz.get_total_cash_in(),
        'total_out': biz.get_total_cash_out(),
        'balance': biz.get_current_balance(),
        'recent_transactions': recent_transactions,
    })


@login_required
@approved_service_admin_required
def business_edit_view(request, business_id):
    biz = get_object_or_404(Business, id=business_id)
    if request.method == 'POST':
        form = BusinessForm(request.POST, instance=biz)
        if form.is_valid():
            form.save()
            messages.success(request, f"Business '{biz.name}' updated successfully.")
            return redirect('businesses:business_detail', business_id=biz.id)
    else:
        form = BusinessForm(instance=biz)

    return render(request, 'businesses/business_form.html', {
        'form': form,
        'business': biz,
        'title': f"Edit {biz.name}",
    })


@login_required
@approved_service_admin_required
def business_delete_view(request, business_id):
    biz = get_object_or_404(Business, id=business_id)
    if request.method == 'POST':
        name = biz.name
        biz.delete()
        messages.success(request, f"Business '{name}' and all its cashbooks have been deleted.")
        return redirect('businesses:business_list')

    return render(request, 'businesses/business_confirm_delete.html', {'business': biz})
