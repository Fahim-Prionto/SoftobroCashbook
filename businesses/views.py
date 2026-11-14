from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum as DjSum
from django.shortcuts import render, redirect, get_object_or_404
from businesses.forms import BusinessForm
from businesses.models import Business
from core.decorators import approved_service_admin_required
from partners.models import PartnerEntry


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
        p_agg = PartnerEntry.objects.filter(business_id=b.id).aggregate(
            total=DjSum('total_amount'), settled=DjSum('settled_amount')
        )
        inv = p_agg['total'] or Decimal('0.00')
        col = p_agg['settled'] or Decimal('0.00')
        due = inv - col
        business_data.append({
            'obj': b,
            'books_count': b.cashbooks.count(),
            'customer_invoiced': inv,
            'customer_settled': col,
            'customer_due': due,
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

    # Aggregate customer entries for this business
    _pb_agg = PartnerEntry.objects.filter(business_id=business_id).aggregate(
        total=DjSum('total_amount'), settled=DjSum('settled_amount')
    )
    customer_invoiced = _pb_agg['total'] or Decimal('0.00')
    customer_settled = _pb_agg['settled'] or Decimal('0.00')
    customer_due = customer_invoiced - customer_settled

    # Per-book metrics for Customer Hisab
    books_with_metrics = []
    for cb in cashbooks:
        cb_agg = PartnerEntry.objects.filter(cashbook_id=cb.id).aggregate(
            total=DjSum('total_amount'), settled=DjSum('settled_amount')
        )
        inv = cb_agg['total'] or Decimal('0.00')
        col = cb_agg['settled'] or Decimal('0.00')
        due = inv - col
        cnt = PartnerEntry.objects.filter(cashbook_id=cb.id).count()
        books_with_metrics.append({
            'book': cb,
            'entries_count': cnt,
            'invoiced': inv,
            'collected': col,
            'due': due,
            'balance': cb.get_current_balance(),
        })

    # Recent customer entries in this business
    recent_customer_entries = list(PartnerEntry.objects.filter(
        business_id=business_id
    ).select_related('partner').order_by('-date_time')[:10])

    cb_map = {cb.id: cb for cb in cashbooks}
    for pe in recent_customer_entries:
        pe.attached_book = cb_map.get(pe.cashbook_id)

    return render(request, 'businesses/business_detail.html', {
        'business': biz,
        'books_with_metrics': books_with_metrics,
        'cashbooks': cashbooks,
        'can_add_cashbook': can_add_cashbook,
        'max_cashbooks': max_cashbooks,
        'customer_invoiced': customer_invoiced,
        'customer_settled': customer_settled,
        'customer_due': customer_due,
        'recent_customer_entries': recent_customer_entries,
        'balance': biz.get_current_balance(),
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
