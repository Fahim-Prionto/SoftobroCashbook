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

    from partners.models import PartnerEntry
    from django.db.models import Sum as DjSum

    cashbook_data = []
    for cb in cashbooks:
        p_agg = PartnerEntry.objects.filter(cashbook_id=cb.id).aggregate(
            tot=DjSum('total_amount'),
            setl=DjSum('settled_amount')
        )
        t_inv = p_agg['tot'] or Decimal('0.00')
        t_setl = p_agg['setl'] or Decimal('0.00')
        cashbook_data.append({
            'obj': cb,
            'total_invoiced': t_inv,
            'total_settled': t_setl,
            'total_outstanding': t_inv - t_setl,
            'entries_count': PartnerEntry.objects.filter(cashbook_id=cb.id).count(),
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
        messages.error(request, f"You have reached your limit of {subscription.plan.max_cashbooks_per_business} books for this business.")
        return redirect('businesses:business_detail', business_id=business.id)

    if request.method == 'POST':
        form = CashbookForm(request.POST)
        if form.is_valid():
            cb = form.save(commit=False)
            cb.business = business
            cb.save()
            messages.success(request, f"Book '{cb.name}' created successfully.")
            return redirect('cashbooks:cashbook_detail', cashbook_id=cb.id)
    else:
        form = CashbookForm()

    return render(request, 'cashbooks/cashbook_form.html', {
        'form': form,
        'business': business,
        'title': f"Add Book to {business.name}",
    })


@login_required
@approved_service_admin_required
def cashbook_detail_view(request, cashbook_id):
    cb = get_object_or_404(Cashbook.objects.select_related('business'), id=cashbook_id)

    from partners.models import Partner, PartnerEntry
    from django.db.models import Sum as DjSum, Q

    entries = PartnerEntry.objects.filter(cashbook_id=cb.id).select_related('partner').prefetch_related('lines', 'receipts').order_by('-date_time')

    # Filtering parameters
    direction = request.GET.get('direction', '')
    payment_status = request.GET.get('payment_status', '')
    partner_id = request.GET.get('partner', '')
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')
    search_q = request.GET.get('q', '').strip()

    if direction:
        entries = entries.filter(direction=direction)
    if payment_status:
        entries = entries.filter(payment_status=payment_status)
    if partner_id:
        entries = entries.filter(partner_id=partner_id)
    if start_date:
        entries = entries.filter(date_time__date__gte=start_date)
    if end_date:
        entries = entries.filter(date_time__date__lte=end_date)
    if search_q:
        entries = entries.filter(
            Q(reference_number__icontains=search_q) |
            Q(remarks__icontains=search_q) |
            Q(partner__name__icontains=search_q) |
            Q(entry_type__icontains=search_q)
        )

    # Aggregates for this book (overall)
    all_entries = PartnerEntry.objects.filter(cashbook_id=cb.id)
    overall_agg = all_entries.aggregate(
        tot=DjSum('total_amount'),
        setl=DjSum('settled_amount')
    )
    total_invoiced = overall_agg['tot'] or Decimal('0.00')
    total_settled = overall_agg['setl'] or Decimal('0.00')
    total_outstanding = total_invoiced - total_settled

    # Filtered aggregates
    filtered_agg = entries.aggregate(
        tot=DjSum('total_amount'),
        setl=DjSum('settled_amount')
    )
    filter_invoiced = filtered_agg['tot'] or Decimal('0.00')
    filter_settled = filtered_agg['setl'] or Decimal('0.00')
    filter_outstanding = filter_invoiced - filter_settled

    partners = Partner.objects.filter(is_active=True).order_by('name')

    return render(request, 'cashbooks/cashbook_detail.html', {
        'cashbook': cb,
        'entries': entries,
        'partners': partners,
        'total_invoiced': total_invoiced,
        'total_settled': total_settled,
        'total_outstanding': total_outstanding,
        'filter_invoiced': filter_invoiced,
        'filter_settled': filter_settled,
        'filter_outstanding': filter_outstanding,
        'entries_count': entries.count(),
        'all_entries_count': all_entries.count(),
        'params': {
            'direction': direction,
            'payment_status': payment_status,
            'partner': partner_id,
            'start_date': start_date,
            'end_date': end_date,
            'q': search_q,
        },
        'filter_directions': [('', 'All Directions'), ('CASH_IN', 'Cash In'), ('CASH_OUT', 'Cash Out')],
        'filter_payment_statuses': [('', 'All Statuses'), ('PAID', 'Paid'), ('PARTIAL', 'Partial'), ('UNPAID', 'Unpaid')],
    })


@login_required
@approved_service_admin_required
def cashbook_edit_view(request, cashbook_id):
    cb = get_object_or_404(Cashbook, id=cashbook_id)
    if request.method == 'POST':
        form = CashbookForm(request.POST, instance=cb)
        if form.is_valid():
            form.save()
            messages.success(request, f"Book '{cb.name}' updated successfully.")
            return redirect('cashbooks:cashbook_detail', cashbook_id=cb.id)
    else:
        form = CashbookForm(instance=cb)

    return render(request, 'cashbooks/cashbook_form.html', {
        'form': form,
        'business': cb.business,
        'cashbook': cb,
        'title': f"Edit Book: {cb.name}",
    })


@login_required
@approved_service_admin_required
def cashbook_delete_view(request, cashbook_id):
    cb = get_object_or_404(Cashbook, id=cashbook_id)
    biz_id = cb.business.id
    if request.method == 'POST':
        name = cb.name
        cb.delete()
        messages.success(request, f"Book '{name}' has been deleted.")
        return redirect('businesses:business_detail', business_id=biz_id)

    return render(request, 'cashbooks/cashbook_confirm_delete.html', {'cashbook': cb})


@login_required
@approved_service_admin_required
def cashbook_print_view(request, cashbook_id):
    cb = get_object_or_404(Cashbook.objects.select_related('business'), id=cashbook_id)

    from partners.models import PartnerEntry, InvoiceCustomization
    from django.db.models import Sum as DjSum

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    entries = PartnerEntry.objects.filter(cashbook_id=cb.id).select_related('partner').prefetch_related('lines').order_by('date_time')
    if start_date:
        entries = entries.filter(date_time__date__gte=start_date)
    if end_date:
        entries = entries.filter(date_time__date__lte=end_date)

    agg = entries.aggregate(tot=DjSum('total_amount'), setl=DjSum('settled_amount'))
    total_invoiced = agg['tot'] or Decimal('0.00')
    total_settled = agg['setl'] or Decimal('0.00')
    total_outstanding = total_invoiced - total_settled

    customization = InvoiceCustomization.objects.filter(
        business_id=cb.business_id, entry__isnull=True
    ).first()
    if not customization:
        customization = InvoiceCustomization.objects.filter(entry__isnull=True).first()

    return render(request, 'cashbooks/cashbook_print.html', {
        'cashbook': cb,
        'business': cb.business,
        'entries': entries,
        'start_date': start_date,
        'end_date': end_date,
        'total_invoiced': total_invoiced,
        'total_settled': total_settled,
        'total_outstanding': total_outstanding,
        'customization': customization,
    })
