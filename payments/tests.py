from decimal import Decimal
from django.test import TestCase
from accounts.models import User, UserRole, AccountStatus
from payments.models import Payment, PaymentStatus
from subscriptions.models import SubscriptionPlan, Subscription, SubscriptionStatus, BillingCycle


class PaymentWorkflowTests(TestCase):
    def setUp(self):
        self.superadmin = User.objects.create_superuser(
            username='admin_boss',
            email='boss@test.com',
            password='Password@123',
            role=UserRole.SUPER_ADMIN,
            status=AccountStatus.ACTIVE,
        )
        self.service_admin = User.objects.create_user(
            username='trader_kamal',
            email='kamal@test.com',
            password='Password@123',
            role=UserRole.SERVICE_ADMIN,
            status=AccountStatus.PENDING_APPROVAL,
            phone_number='01700112233',
        )
        self.plan = SubscriptionPlan.objects.create(
            name='Standard Plan',
            slug='standard-plan',
            billing_cycle=BillingCycle.MONTHLY,
            duration_days=30,
            price_bdt=Decimal('999.00'),
            max_businesses=1,
            max_cashbooks_per_business=5,
            max_transactions=0,
            is_active=True,
        )

    def test_payment_submission_and_status(self):
        payment = Payment.objects.create(
            service_admin=self.service_admin,
            plan=self.plan,
            amount_bdt=self.plan.price_bdt,
            bkash_transaction_id='9X2K4L7M10',
            sender_bkash_number='01700112233',
            status=PaymentStatus.PENDING,
        )
        self.assertEqual(payment.status, PaymentStatus.PENDING)
        self.assertEqual(payment.amount_bdt, Decimal('999.00'))
        self.assertEqual(self.service_admin.status, AccountStatus.PENDING_APPROVAL)

    def test_payment_approval_activates_account(self):
        payment = Payment.objects.create(
            service_admin=self.service_admin,
            plan=self.plan,
            amount_bdt=self.plan.price_bdt,
            bkash_transaction_id='9X2K4L7M11',
            sender_bkash_number='01700112233',
            status=PaymentStatus.PENDING,
        )

        # Super Admin approves payment
        payment.status = PaymentStatus.APPROVED
        payment.approved_by = self.superadmin
        payment.admin_notes = "Verified via bKash statement"
        payment.save()

        # Update service admin status
        self.service_admin.status = AccountStatus.ACTIVE
        self.service_admin.save()

        self.service_admin.refresh_from_db()
        self.assertTrue(self.service_admin.is_approved)
        self.assertEqual(payment.status, PaymentStatus.APPROVED)
