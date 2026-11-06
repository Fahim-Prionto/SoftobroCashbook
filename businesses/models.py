from decimal import Decimal
from django.db import models


class Business(models.Model):
    name = models.CharField(max_length=200, help_text="Name of the business entity")
    address = models.TextField(blank=True, help_text="Physical or office address")
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    description = models.TextField(blank=True)
    opening_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Initial capital or starting cash balance in BDT",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Business'
        verbose_name_plural = 'Businesses'
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_total_cash_in(self) -> Decimal:
        from transactions.models import Transaction, TransactionType
        result = Transaction.objects.filter(
            cashbook__business=self,
            transaction_type=TransactionType.CASH_IN,
        ).aggregate(total=models.Sum('amount'))['total']
        return result or Decimal('0.00')

    def get_total_cash_out(self) -> Decimal:
        from transactions.models import Transaction, TransactionType
        result = Transaction.objects.filter(
            cashbook__business=self,
            transaction_type=TransactionType.CASH_OUT,
        ).aggregate(total=models.Sum('amount'))['total']
        return result or Decimal('0.00')

    def get_current_balance(self) -> Decimal:
        cashbooks = self.cashbooks.all()
        # Total balance is opening balances of cashbooks + all cash-in - all cash-out
        total_cb_opening = sum((cb.opening_balance for cb in cashbooks), Decimal('0.00'))
        return self.opening_balance + total_cb_opening + self.get_total_cash_in() - self.get_total_cash_out()

    def get_partner_total_amount(self) -> Decimal:
        from partners.models import PartnerEntry
        from django.db.models import Sum
        result = PartnerEntry.objects.filter(
            business_id=self.pk
        ).aggregate(total=Sum('total_amount'))['total']
        return result or Decimal('0.00')

    def get_partner_outstanding(self) -> Decimal:
        from partners.models import PartnerEntry
        from django.db.models import Sum
        agg = PartnerEntry.objects.filter(business_id=self.pk).aggregate(
            total=Sum('total_amount'), settled=Sum('settled_amount')
        )
        total = agg['total'] or Decimal('0.00')
        settled = agg['settled'] or Decimal('0.00')
        return total - settled
