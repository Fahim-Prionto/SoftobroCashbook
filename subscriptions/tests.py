from decimal import Decimal
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from accounts.models import User, UserRole, AccountStatus
from subscriptions.models import SubscriptionPlan, Subscription, SubscriptionStatus, BillingCycle


class SubscriptionPlanAndLimitTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='merchant1',
            email='merchant1@test.com',
            password='Password@123',
            role=UserRole.SERVICE_ADMIN,
            status=AccountStatus.ACTIVE,
        )
        self.plan = SubscriptionPlan.objects.create(
            name='Test Starter',
            slug='test-starter',
            billing_cycle=BillingCycle.MONTHLY,
            duration_days=30,
            price_bdt=Decimal('500.00'),
            max_businesses=2,
            max_cashbooks_per_business=3,
            max_transactions=100,
            is_active=True,
        )

    def test_plan_limits_enforcement(self):
        now = timezone.now()
        sub = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            status=SubscriptionStatus.ACTIVE,
            start_date=now,
            end_date=now + timedelta(days=30),
            grace_period_days=7,
        )

        self.assertTrue(sub.is_currently_active)
        self.assertGreater(sub.remaining_days, 28)

        # Business limit tests
        self.assertTrue(sub.can_create_business(current_count=0))
        self.assertTrue(sub.can_create_business(current_count=1))
        self.assertFalse(sub.can_create_business(current_count=2))

        # Cashbook limit tests
        self.assertTrue(sub.can_create_cashbook(current_count=0))
        self.assertTrue(sub.can_create_cashbook(current_count=2))
        self.assertFalse(sub.can_create_cashbook(current_count=3))

        # Transaction limit tests
        self.assertTrue(sub.can_create_transaction(current_count=99))
        self.assertFalse(sub.can_create_transaction(current_count=100))

    def test_expired_subscription_blocks_creation(self):
        now = timezone.now()
        # Expired past grace period
        sub = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            status=SubscriptionStatus.EXPIRED,
            start_date=now - timedelta(days=50),
            end_date=now - timedelta(days=20),
            grace_period_days=7,
        )
        self.assertFalse(sub.is_currently_active)
        self.assertFalse(sub.is_in_grace_period)
        self.assertFalse(sub.can_create_business(current_count=0))
