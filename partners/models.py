from decimal import Decimal
from django.db import models
from django.utils import timezone


class PartnerType(models.TextChoices):
    CUSTOMER = 'CUSTOMER', 'Customer'
    VENDOR = 'VENDOR', 'Vendor'
    BOTH = 'BOTH', 'Customer & Vendor'


class PaymentMethod(models.TextChoices):
    CASH = 'CASH', 'Cash'
    BANK = 'BANK', 'Bank Transfer'
    BKASH = 'BKASH', 'bKash'
    NAGAD = 'NAGAD', 'Nagad'
    ROCKET = 'ROCKET', 'Rocket'
    CHEQUE = 'CHEQUE', 'Cheque'
    OTHER = 'OTHER', 'Other'


class UnitOfMeasure(models.TextChoices):
    PCS = 'pcs', 'Pcs'
    KG = 'kg', 'Kg'
    LITRE = 'litre', 'Litre'
    METER = 'meter', 'Meter'
    BOX = 'box', 'Box'
    DOZEN = 'dozen', 'Dozen'
    HOUR = 'hour', 'Hour'
    DAY = 'day', 'Day'
    SET = 'set', 'Set'
    OTHER = 'other', 'Other'


class Partner(models.Model):
    """A partner (customer or vendor) linked to a Service Admin's tenant."""
    name = models.CharField(max_length=200)
    partner_type = models.CharField(
        max_length=10,
        choices=PartnerType.choices,
        default=PartnerType.CUSTOMER,
        db_index=True,
    )
    phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Partner'
        verbose_name_plural = 'Partners'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_partner_type_display()})"

    def get_total_amount(self):
        return self.entries.aggregate(
            total=models.Sum('total_amount')
        )['total'] or Decimal('0.00')

    def get_total_received(self):
        return self.entries.aggregate(
            total=models.Sum('settled_amount')
        )['total'] or Decimal('0.00')

    def get_outstanding(self):
        return self.get_total_amount() - self.get_total_received()


def _next_reference():
    """Generate auto reference: CB/YYYY/NNNNN"""
    year = timezone.now().year
    prefix = f"CB/{year}/"
    last = PartnerEntry.objects.filter(
        reference_number__startswith=prefix
    ).order_by('-reference_number').first()
    if last:
        try:
            seq = int(last.reference_number.split('/')[-1]) + 1
        except (ValueError, IndexError):
            seq = 1
    else:
        seq = 1
    return f"{prefix}{seq:05d}"


class EntryDirection(models.TextChoices):
    CASH_IN = 'CASH_IN', 'Cash In'
    CASH_OUT = 'CASH_OUT', 'Cash Out'


class PaymentStatus(models.TextChoices):
    UNPAID = 'UNPAID', 'Unpaid'
    PARTIAL = 'PARTIAL', 'Partial'
    PAID = 'PAID', 'Paid'


class PartnerEntry(models.Model):
    """
    A ledger entry (like an invoice/bill) linked to a Partner.
    Can have multiple line items and multiple receipt payments.
    """
    reference_number = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
        db_index=True,
    )
    partner = models.ForeignKey(
        Partner,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='entries',
    )
    business = models.ForeignKey(
        'businesses.Business',
        on_delete=models.CASCADE,
        related_name='partner_entries',
    )
    cashbook = models.ForeignKey(
        'cashbooks.Cashbook',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='partner_entries',
    )
    direction = models.CharField(
        max_length=10,
        choices=EntryDirection.choices,
        default=EntryDirection.CASH_IN,
        db_index=True,
    )
    entry_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="e.g. Income, Expense, Sales, Purchase",
    )
    date_time = models.DateTimeField(default=timezone.now, db_index=True)
    remarks = models.TextField(blank=True)

    # Computed totals — updated on save via signal/method
    total_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    settled_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    payment_status = models.CharField(
        max_length=10,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
        db_index=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Partner Entry'
        verbose_name_plural = 'Partner Entries'
        ordering = ['-date_time']

    def __str__(self):
        return f"{self.reference_number} – {self.partner} [{self.direction}]"

    def save(self, *args, **kwargs):
        if not self.reference_number:
            self.reference_number = _next_reference()
        super().save(*args, **kwargs)

    def recalculate_totals(self):
        """Recompute total_amount from lines and settled_amount from receipts."""
        line_total = self.lines.aggregate(
            t=models.Sum(
                models.ExpressionWrapper(
                    models.F('price') * models.F('quantity'),
                    output_field=models.DecimalField(max_digits=14, decimal_places=2)
                )
            )
        )['t'] or Decimal('0.00')

        receipt_total = self.receipts.aggregate(
            t=models.Sum('amount')
        )['t'] or Decimal('0.00')

        self.total_amount = line_total
        self.settled_amount = receipt_total

        if receipt_total <= 0:
            self.payment_status = PaymentStatus.UNPAID
        elif receipt_total >= line_total:
            self.payment_status = PaymentStatus.PAID
        else:
            self.payment_status = PaymentStatus.PARTIAL

        PartnerEntry.objects.filter(pk=self.pk).update(
            total_amount=self.total_amount,
            settled_amount=self.settled_amount,
            payment_status=self.payment_status,
        )

    @property
    def outstanding_amount(self):
        return self.total_amount - self.settled_amount


class PartnerEntryLine(models.Model):
    """An individual line item within a PartnerEntry."""
    entry = models.ForeignKey(
        PartnerEntry,
        on_delete=models.CASCADE,
        related_name='lines',
    )
    description = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    quantity = models.DecimalField(max_digits=10, decimal_places=3, default=Decimal('1.000'))
    uom = models.CharField(
        max_length=10,
        choices=UnitOfMeasure.choices,
        default=UnitOfMeasure.PCS,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Entry Line'
        verbose_name_plural = 'Entry Lines'
        ordering = ['id']

    def __str__(self):
        return f"{self.description} × {self.quantity} {self.uom} @ {self.price}"

    @property
    def line_total(self):
        return (self.price * self.quantity).quantize(Decimal('0.01'))


class PartnerReceipt(models.Model):
    """A payment receipt attached to a PartnerEntry."""
    entry = models.ForeignKey(
        PartnerEntry,
        on_delete=models.CASCADE,
        related_name='receipts',
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    payment_method = models.CharField(
        max_length=10,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
    )
    received_at = models.DateTimeField(default=timezone.now)
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Partner Receipt'
        verbose_name_plural = 'Partner Receipts'
        ordering = ['received_at']

    def __str__(self):
        return f"Receipt ৳{self.amount} via {self.payment_method} for {self.entry.reference_number}"


class InvoiceTemplate(models.Model):
    """A blank PDF template that the Super/Service admin uploads for custom invoice printing."""
    name = models.CharField(max_length=100)
    pdf_file = models.FileField(upload_to='invoice_templates/')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Invoice Template'
        verbose_name_plural = 'Invoice Templates'
        ordering = ['-created_at']

    def __str__(self):
        return self.name
