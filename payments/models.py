from django.conf import settings
from django.db import models
from django.utils import timezone


class PaymentStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Verification'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'


class Payment(models.Model):
    service_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments',
    )
    plan = models.ForeignKey(
        'subscriptions.SubscriptionPlan',
        on_delete=models.PROTECT,
        related_name='payments',
    )
    amount_bdt = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Amount paid in BDT",
    )
    bkash_transaction_id = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="bKash TrxID from SMS (e.g. 9J4K2L8A)",
    )
    sender_bkash_number = models.CharField(
        max_length=30,
        help_text="The bKash mobile number from which payment was sent",
    )
    payment_screenshot = models.ImageField(
        upload_to='payments/screenshots/',
        blank=True,
        null=True,
        help_text="Optional screenshot of the bKash transaction confirmation",
    )
    payment_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        db_index=True,
    )
    approval_date = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_payments',
    )
    admin_notes = models.TextField(blank=True, help_text="Notes from Super Admin verification")
    is_renewal = models.BooleanField(default=False, help_text="Is this a renewal payment?")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        ordering = ['-created_at']

    def __str__(self):
        return f"Payment #{self.id} - {self.service_admin.username} - {self.bkash_transaction_id} ({self.get_status_display()})"
