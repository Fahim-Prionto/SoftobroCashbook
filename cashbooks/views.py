from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q
from django.shortcuts import render, redirect, get_object_or_404
from businesses.models import Business
from cashbooks.forms import CashbookForm
from cashbooks.models import Cashbook, CashbookStatus
from core.decorators import approved_service_admin_required
from transactions.models import Transaction, TransactionType


@login_required
@approved_service_admin_required
def cashbook_list_view(request):
    cashbooks = Cashbook.objects.select_related('business').all()
    status_filter = request.GET.get('status')
    business_id = request.GET.get('business')

    if status_filter:
        cashbooks = cashbooks.filter(status=status_filter)
    if business_id:
        cashbooks = cashbooks.filter(business_id=business_id)

    businesses = Business.objects.all()

    cashbook_data = []
    for cb in cashbooks:
        cashbook_data.append({
            'obj': cb,
            'total_in': cb.get_total_cash_in(),
            'total_out': cb.get_total_cash_out(),
            'balance': cb.get_current_balance(),
        })

    return render(request, 'cashbooks/cashbook_list.html', {
        'cashbooks': cashbook_data,
        'businesses': businesses,
        'selected_business': business_id,
        'selected_status': status_filter,
    })


@login_required
@approved_service_admin_required
def cashbook_create_view(request, business_id):
    business = get_object_or_404(Business, id=business_id)
    subscription = getattr(request.user, 'subscription', None)

    current_cashbooks = business.cashbooks.count()
    if subscription and not subscription.can_create_cashbook(current_cashbooks):
        messages.error(request, f"You have reached your limit of {subscription.plan.max_cashbooks_per_business} cashbooks for this business.")
        return redirect('businesses:business_detail', business_id=business.id)

    if request.method == 'POST':
        form = CashbookForm(request.POST)
        if form.is_valid():
            cb = form.save(commit=False)
            cb.business = business
            cb.save()
            messages.success(request, f"Cashbook '{cb.name}' created successfully.")
            return redirect('cashbooks:cashbook_detail', cashbook_id=cb.id)
    else:
        form = CashbookForm()

    return render(request, 'cashbooks/cashbook_form.html', {
        'form': form,
        'business': business,
        'title': f"Add Cashbook to {business.name}",
    })


@login_required
@approved_service_admin_required
def cashbook_detail_view(request, cashbook_id):
    cb = get_object_or_404(Cashbook.objects.select_related('business'), id=cashbook_id)

    # Filtering parameters
    trans_type = request.GET.get('type')
    category = request.GET.get('category')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    search_q = request.GET.get('q', '').strip()

    transactions = cb.transactions.all()

    if trans_type:
        transactions = transactions.filter(transaction_type=trans_type)
    if category:
        transactions = transactions.filter(category=category)
    if start_date:
        transactions = transactions.filter(date__gte=start_date)
    if end_date:
        transactions = transactions.filter(date__lte=end_date)
    if search_q:
        transactions = transactions.filter(
            Q(description__icontains=search_q) |
            Q(reference_number__icontains=search_q) |
            Q(category__icontains=search_q)
        )

    # Categories for filter dropdown
    available_categories = cb.transactions.values_list('category', flat=True).distinct()

    # Dynamic totals based on current filters
    filter_in = transactions.filter(transaction_type=TransactionType.CASH_IN).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    filter_out = transactions.filter(transaction_type=TransactionType.CASH_OUT).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    # Overall cashbook totals
    overall_in = cb.get_total_cash_in()
    overall_out = cb.get_total_cash_out()
    overall_balance = cb.get_current_balance()

    from partners.models import PartnerEntry
    from django.db.models import Sum as DjSum2
    _cb_pb_agg = PartnerEntry.objects.filter(cashbook_id=cb.id).aggregate(
        total=DjSum2('total_amount'), settled=DjSum2('settled_amount')
    )
    partner_total = _cb_pb_agg['total'] or Decimal('0.00')
    partner_settled = _cb_pb_agg['settled'] or Decimal('0.00')
    partner_outstanding = partner_total - partner_settled
    recent_partner_entries = PartnerEntry.objects.filter(
        cashbook_id=cb.id
    ).select_related('partner').order_by('-date_time')[:5]

    return render(request, 'cashbooks/cashbook_detail.html', {
        'cashbook': cb,
        'transactions': transactions,
        'available_categories': available_categories,
        'filter_in': filter_in,
        'filter_out': filter_out,
        'overall_in': overall_in,
        'overall_out': overall_out,
        'overall_balance': overall_balance,
        'partner_total': partner_total,
        'partner_settled': partner_settled,
        'partner_outstanding': partner_outstanding,
        'recent_partner_entries': recent_partner_entries,
        'params': {
            'type': trans_type,
            'category': category,
            'start_date': start_date,
            'end_date': end_date,
            'q': search_q,
        }
    })


@login_required
@approved_service_admin_required
def cashbook_edit_view(request, cashbook_id):
    cb = get_object_or_404(Cashbook, id=cashbook_id)
    if request.method == 'POST':
        form = CashbookForm(request.POST, instance=cb)
        if form.is_valid():
            form.save()
            messages.success(request, f"Cashbook '{cb.name}' updated successfully.")
            return redirect('cashbooks:cashbook_detail', cashbook_id=cb.id)
    else:
        form = CashbookForm(instance=cb)

    return render(request, 'cashbooks/cashbook_form.html', {
        'form': form,
        'business': cb.business,
        'cashbook': cb,
        'title': f"Edit Cashbook: {cb.name}",
    })


@login_required
@approved_service_admin_required
def cashbook_delete_view(request, cashbook_id):
    cb = get_object_or_404(Cashbook, id=cashbook_id)
    biz_id = cb.business.id
    if request.method == 'POST':
        name = cb.name
        cb.delete()
        messages.success(request, f"Cashbook '{name}' and its transactions have been deleted.")
        return redirect('businesses:business_detail', business_id=biz_id)

    return render(request, 'cashbooks/cashbook_confirm_delete.html', {'cashbook': cb})


@login_required
@approved_service_admin_required
def cashbook_print_view(request, cashbook_id):
    cb = get_object_or_404(Cashbook.objects.select_related('business'), id=cashbook_id)

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    transactions = cb.transactions.all().order_by('date', 'created_at')
    if start_date:
        transactions = transactions.filter(date__gte=start_date)
    if end_date:
        transactions = transactions.filter(date__lte=end_date)

    total_in = transactions.filter(transaction_type=TransactionType.CASH_IN).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')
    total_out = transactions.filter(transaction_type=TransactionType.CASH_OUT).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')
    net_period = total_in - total_out
    closing_balance = cb.opening_balance + total_in - total_out

    return render(request, 'cashbooks/cashbook_print.html', {
        'cashbook': cb,
        'business': cb.business,
        'transactions': transactions,
        'start_date': start_date,
        'end_date': end_date,
        'total_in': total_in,
        'total_out': total_out,
        'net_period': net_period,
        'closing_balance': closing_balance,
    })
