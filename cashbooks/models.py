from decimal import Decimal
from django.db import models


class CashbookStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    ARCHIVED = 'ARCHIVED', 'Archived'


class Cashbook(models.Model):
    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.CASCADE,
        related_name='cashbooks',
    )
    name = models.CharField(max_length=150, help_text="Cashbook name (e.g., Daily Cash, Petty Cash, Bank Account)")
    opening_balance = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text="Starting balance in BDT",
    )
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=CashbookStatus.choices,
        default=CashbookStatus.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Cashbook'
        verbose_name_plural = 'Cashbooks'
        ordering = ['business', 'name']

    def __str__(self):
        return f"{self.business.name} - {self.name}"

    def get_total_cash_in(self) -> Decimal:
        from transactions.models import Transaction, TransactionType
        result = self.transactions.filter(
            transaction_type=TransactionType.CASH_IN,
        ).aggregate(total=models.Sum('amount'))['total']
        return result or Decimal('0.00')

    def get_total_cash_out(self) -> Decimal:
        from transactions.models import Transaction, TransactionType
        result = self.transactions.filter(
            transaction_type=TransactionType.CASH_OUT,
        ).aggregate(total=models.Sum('amount'))['total']
        return result or Decimal('0.00')

    def get_current_balance(self) -> Decimal:
        return self.opening_balance + self.get_total_cash_in() - self.get_total_cash_out()
