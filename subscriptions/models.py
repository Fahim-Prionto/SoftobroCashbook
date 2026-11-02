from datetime import timedelta
from django.conf import settings
from django.db import models
from django.utils import timezone


class BillingCycle(models.TextChoices):
    MONTHLY = 'MONTHLY', 'Monthly'
    QUARTERLY = 'QUARTERLY', 'Quarterly'
    YEARLY = 'YEARLY', 'Yearly'
    CUSTOM = 'CUSTOM', 'Custom Duration'


class SubscriptionStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending Approval'
    ACTIVE = 'ACTIVE', 'Active'
    EXPIRED = 'EXPIRED', 'Expired'
    SUSPENDED = 'SUSPENDED', 'Suspended'


class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    billing_cycle = models.CharField(
        max_length=20,
        choices=BillingCycle.choices,
        default=BillingCycle.MONTHLY,
    )
    duration_days = models.PositiveIntegerField(
        default=30,
        help_text="Duration in days. E.g., 30 for 1 month, 90 for 3 months, 365 for 1 year.",
    )
    price_bdt = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Price in Bangladeshi Taka (BDT ৳)",
    )
    max_businesses = models.PositiveIntegerField(
        default=1,
        help_text="Maximum allowed businesses for this plan",
    )
    max_cashbooks_per_business = models.PositiveIntegerField(
        default=3,
        help_text="Maximum cashbooks per business",
    )
    max_transactions = models.PositiveIntegerField(
        default=0,
        help_text="Maximum transactions per month (0 means unlimited)",
    )
    features_list = models.TextField(
        help_text="Enter features separated by line breaks or commas",
        blank=True,
    )
    is_active = models.BooleanField(default=True, db_index=True)
    is_popular = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Subscription Plan'
        verbose_name_plural = 'Subscription Plans'
        ordering = ['price_bdt']

    def __str__(self):
        return f"{self.name} - ৳{self.price_bdt} ({self.get_billing_cycle_display()})"

    def get_features_list(self):
        if not self.features_list:
            return []
        lines = [line.strip() for line in self.features_list.splitlines() if line.strip()]
        if len(lines) == 1 and ',' in lines[0]:
            return [x.strip() for x in lines[0].split(',') if x.strip()]
        return lines


class Subscription(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscription',
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name='user_subscriptions',
    )
    status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.PENDING,
        db_index=True,
    )
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    grace_period_days = models.PositiveIntegerField(default=7)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Subscription'
        verbose_name_plural = 'Subscriptions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.plan.name} ({self.get_status_display()})"

    @property
    def is_currently_active(self):
        if self.status != SubscriptionStatus.ACTIVE:
            return False
        if not self.end_date:
            return False
        return timezone.now() <= self.end_date

    @property
    def is_in_grace_period(self):
        if self.status != SubscriptionStatus.ACTIVE and self.status != SubscriptionStatus.EXPIRED:
            return False
        if not self.end_date:
            return False
        now = timezone.now()
        grace_end = self.end_date + timedelta(days=self.grace_period_days)
        return self.end_date < now <= grace_end

    @property
    def remaining_days(self):
        if not self.end_date:
            return 0
        diff = self.end_date - timezone.now()
        return max(0, diff.days)

    def can_create_business(self, current_count: int) -> bool:
        if not self.is_currently_active and not self.is_in_grace_period:
            return False
        return current_count < self.plan.max_businesses

    def can_create_cashbook(self, current_count: int) -> bool:
        if not self.is_currently_active and not self.is_in_grace_period:
            return False
        return current_count < self.plan.max_cashbooks_per_business

    def can_create_transaction(self, current_count: int) -> bool:
        if not self.is_currently_active and not self.is_in_grace_period:
            return False
        if self.plan.max_transactions == 0:
            return True
        return current_count < self.plan.max_transactions
