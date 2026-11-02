from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from decimal import Decimal


class TransactionType(models.TextChoices):
    CASH_IN = 'CASH_IN', 'Cash In (+)'
    CASH_OUT = 'CASH_OUT', 'Cash Out (-)'


class Transaction(models.Model):
    cashbook = models.ForeignKey(
        'cashbooks.Cashbook',
        on_delete=models.CASCADE,
        related_name='transactions',
    )
    transaction_type = models.CharField(
        max_length=10,
        choices=TransactionType.choices,
        db_index=True,
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Transaction amount in BDT",
    )
    date = models.DateField(default=timezone.now, db_index=True)
    category = models.CharField(
        max_length=100,
        db_index=True,
        help_text="e.g. Sales, Service, Rent, Salary, Utility, Inventory, etc.",
    )
    description = models.TextField(blank=True)
    reference_number = models.CharField(
        max_length=100,
        blank=True,
        help_text="Receipt, voucher, or invoice reference number",
    )
    attachment = models.FileField(
        upload_to='transactions/attachments/',
        blank=True,
        null=True,
        help_text="Optional receipt or invoice attachment",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        ordering = ['-date', '-created_at']

    def __str__(self):
        sign = '+' if self.transaction_type == TransactionType.CASH_IN else '-'
        return f"[{self.date}] {self.cashbook.name}: {sign}৳{self.amount} ({self.category})"
