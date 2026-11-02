from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from cashbooks.models import Cashbook
from core.decorators import approved_service_admin_required
from transactions.forms import TransactionForm
from transactions.models import Transaction, TransactionType


@login_required
@approved_service_admin_required
def transaction_create_view(request, cashbook_id):
    cashbook = get_object_or_404(Cashbook.objects.select_related('business'), id=cashbook_id)
    subscription = getattr(request.user, 'subscription', None)

    if subscription:
        current_trans_count = Transaction.objects.count()
        if not subscription.can_create_transaction(current_trans_count):
            messages.error(request, f"You have reached your limit of {subscription.plan.max_transactions} transactions for your plan. Please upgrade to continue.")
            return redirect('cashbooks:cashbook_detail', cashbook_id=cashbook.id)

    default_type = request.GET.get('type', TransactionType.CASH_IN)

    if request.method == 'POST':
        form = TransactionForm(request.POST, request.FILES)
        if form.is_valid():
            trans = form.save(commit=False)
            trans.cashbook = cashbook
            trans.save()
            type_label = "Cash In" if trans.transaction_type == TransactionType.CASH_IN else "Cash Out"
            messages.success(request, f"{type_label} of ৳{trans.amount:,.2f} recorded successfully.")
            return redirect('cashbooks:cashbook_detail', cashbook_id=cashbook.id)
    else:
        form = TransactionForm(initial={'transaction_type': default_type})

    return render(request, 'transactions/transaction_form.html', {
        'form': form,
        'cashbook': cashbook,
        'business': cashbook.business,
        'default_type': default_type,
        'title': f"Add Transaction - {cashbook.name}",
    })


@login_required
@approved_service_admin_required
def transaction_edit_view(request, transaction_id):
    trans = get_object_or_404(Transaction.objects.select_related('cashbook__business'), id=transaction_id)
    cashbook = trans.cashbook

    if request.method == 'POST':
        form = TransactionForm(request.POST, request.FILES, instance=trans)
        if form.is_valid():
            form.save()
            messages.success(request, f"Transaction #{trans.id} updated successfully.")
            return redirect('cashbooks:cashbook_detail', cashbook_id=cashbook.id)
    else:
        form = TransactionForm(instance=trans)

    return render(request, 'transactions/transaction_form.html', {
        'form': form,
        'cashbook': cashbook,
        'business': cashbook.business,
        'transaction': trans,
        'title': f"Edit Transaction #{trans.id}",
    })


@login_required
@approved_service_admin_required
def transaction_delete_view(request, transaction_id):
    trans = get_object_or_404(Transaction.objects.select_related('cashbook'), id=transaction_id)
    cashbook_id = trans.cashbook.id

    if request.method == 'POST':
        trans.delete()
        messages.success(request, "Transaction deleted successfully.")
        return redirect('cashbooks:cashbook_detail', cashbook_id=cashbook_id)

    return render(request, 'transactions/transaction_confirm_delete.html', {
        'transaction': trans,
        'cashbook': trans.cashbook,
    })
