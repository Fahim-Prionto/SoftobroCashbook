from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q, Count
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from businesses.models import Business
from cashbooks.models import Cashbook
from core.decorators import approved_service_admin_required
from transactions.models import Transaction, TransactionType


@login_required
@approved_service_admin_required
def report_dashboard_view(request):
    businesses = Business.objects.all()
    cashbooks = Cashbook.objects.all()
    today = timezone.now().date()
    current_month_start = today.replace(day=1)

    # Monthly totals across entire tenant
    monthly_in = Transaction.objects.filter(
        date__gte=current_month_start,
        date__lte=today,
        transaction_type=TransactionType.CASH_IN
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')

    monthly_out = Transaction.objects.filter(
        date__gte=current_month_start,
        date__lte=today,
        transaction_type=TransactionType.CASH_OUT
    ).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')

    # Total all-time
    total_in = Transaction.objects.filter(transaction_type=TransactionType.CASH_IN).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')
    total_out = Transaction.objects.filter(transaction_type=TransactionType.CASH_OUT).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')

    # Total opening balances
    total_opening = sum((b.opening_balance for b in businesses), Decimal('0.00')) + sum((cb.opening_balance for cb in cashbooks), Decimal('0.00'))
    net_balance = total_opening + total_in - total_out

    return render(request, 'reports/report_dashboard.html', {
        'businesses': businesses,
        'cashbooks': cashbooks,
        'today': today,
        'monthly_in': monthly_in,
        'monthly_out': monthly_out,
        'monthly_net': monthly_in - monthly_out,
        'total_in': total_in,
        'total_out': total_out,
        'net_balance': net_balance,
    })


@login_required
@approved_service_admin_required
def cashbook_report_view(request, cashbook_id):
    cb = get_object_or_404(Cashbook.objects.select_related('business'), id=cashbook_id)
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    trans_type = request.GET.get('type')
    category = request.GET.get('category')

    transactions = cb.transactions.all().order_by('date', 'created_at')

    if start_date:
        transactions = transactions.filter(date__gte=start_date)
    if end_date:
        transactions = transactions.filter(date__lte=end_date)
    if trans_type:
        transactions = transactions.filter(transaction_type=trans_type)
    if category:
        transactions = transactions.filter(category=category)

    total_in = transactions.filter(transaction_type=TransactionType.CASH_IN).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')
    total_out = transactions.filter(transaction_type=TransactionType.CASH_OUT).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')
    closing_balance = cb.opening_balance + total_in - total_out

    return render(request, 'reports/cashbook_report.html', {
        'cashbook': cb,
        'business': cb.business,
        'transactions': transactions,
        'start_date': start_date,
        'end_date': end_date,
        'selected_type': trans_type,
        'selected_category': category,
        'total_in': total_in,
        'total_out': total_out,
        'net_period': total_in - total_out,
        'closing_balance': closing_balance,
        'is_print': 'print' in request.GET,
    })


@login_required
@approved_service_admin_required
def business_summary_report_view(request, business_id):
    business = get_object_or_404(Business.objects.prefetch_related('cashbooks'), id=business_id)
    cashbooks = business.cashbooks.all()

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    cb_summaries = []
    total_in = Decimal('0.00')
    total_out = Decimal('0.00')
    total_opening = business.opening_balance

    for cb in cashbooks:
        qs = cb.transactions.all()
        if start_date:
            qs = qs.filter(date__gte=start_date)
        if end_date:
            qs = qs.filter(date__lte=end_date)

        cb_in = qs.filter(transaction_type=TransactionType.CASH_IN).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')
        cb_out = qs.filter(transaction_type=TransactionType.CASH_OUT).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')
        cb_balance = cb.opening_balance + cb_in - cb_out

        total_in += cb_in
        total_out += cb_out
        total_opening += cb.opening_balance

        cb_summaries.append({
            'cashbook': cb,
            'opening_balance': cb.opening_balance,
            'total_in': cb_in,
            'total_out': cb_out,
            'net_flow': cb_in - cb_out,
            'balance': cb_balance,
            'count': qs.count(),
        })

    net_financial_position = total_opening + total_in - total_out

    return render(request, 'reports/business_summary.html', {
        'business': business,
        'cb_summaries': cb_summaries,
        'total_opening': total_opening,
        'total_in': total_in,
        'total_out': total_out,
        'net_financial_position': net_financial_position,
        'start_date': start_date,
        'end_date': end_date,
        'is_print': 'print' in request.GET,
    })


@login_required
@approved_service_admin_required
def date_range_report_view(request):
    businesses = Business.objects.all()
    cashbooks = Cashbook.objects.all()

    business_id = request.GET.get('business')
    cashbook_id = request.GET.get('cashbook')
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    trans_type = request.GET.get('type')

    transactions = Transaction.objects.select_related('cashbook__business').order_by('date', 'created_at')

    if business_id:
        transactions = transactions.filter(cashbook__business_id=business_id)
    if cashbook_id:
        transactions = transactions.filter(cashbook_id=cashbook_id)
    if start_date:
        transactions = transactions.filter(date__gte=start_date)
    if end_date:
        transactions = transactions.filter(date__lte=end_date)
    if trans_type:
        transactions = transactions.filter(transaction_type=trans_type)

    total_in = transactions.filter(transaction_type=TransactionType.CASH_IN).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')
    total_out = transactions.filter(transaction_type=TransactionType.CASH_OUT).aggregate(t=Sum('amount'))['t'] or Decimal('0.00')

    return render(request, 'reports/date_range_report.html', {
        'transactions': transactions,
        'businesses': businesses,
        'cashbooks': cashbooks,
        'selected_business': business_id,
        'selected_cashbook': cashbook_id,
        'start_date': start_date,
        'end_date': end_date,
        'selected_type': trans_type,
        'total_in': total_in,
        'total_out': total_out,
        'net_flow': total_in - total_out,
        'is_print': 'print' in request.GET,
    })
