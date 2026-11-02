from decimal import Decimal
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import User, UserRole, AccountStatus
from payments.models import Payment, PaymentStatus
from subscriptions.models import SubscriptionPlan, Subscription, SubscriptionStatus, BillingCycle
from tenants.models import Tenant, TenantStatus
from tenants.provisioning import provision_tenant_database, ensure_tenant_database_registered
from tenants.context import set_current_tenant_alias, clear_current_tenant_alias


class Command(BaseCommand):
    help = "Seeds initial super admin, subscription plans, and demo service admin with tenant data."

    def handle(self, *args, **options):
        self.stdout.write("Seeding SoftobroCashBook initial & demo data...")

        # 1. Super Admin
        super_admin, created = User.objects.get_or_create(
            username='superadmin',
            defaults={
                'email': 'admin@softobrocashbook.com',
                'first_name': 'Super',
                'last_name': 'Administrator',
                'role': UserRole.SUPER_ADMIN,
                'status': AccountStatus.ACTIVE,
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            super_admin.set_password('Password@123')
            super_admin.save()
            self.stdout.write(self.style.SUCCESS("Created Super Admin: superadmin / Password@123"))
        else:
            self.stdout.write("Super Admin already exists.")

        # 2. Subscription Plans
        plans_data = [
            {
                'name': 'Starter Plan',
                'slug': 'starter-plan',
                'description': 'Ideal for single retail shops, kiosks, and sole traders.',
                'billing_cycle': BillingCycle.MONTHLY,
                'duration_days': 30,
                'price_bdt': Decimal('499.00'),
                'max_businesses': 1,
                'max_cashbooks_per_business': 3,
                'max_transactions': 0,
                'features_list': "1 Business Entity\nUp to 3 Cashbooks\nUnlimited Transactions\nManual bKash Verification\nA4 Print Statements",
                'is_active': True,
                'is_popular': False,
            },
            {
                'name': 'Growth Plan',
                'slug': 'growth-plan',
                'description': 'Best for multi-outlet retailers, distributors, and expanding businesses.',
                'billing_cycle': BillingCycle.QUARTERLY,
                'duration_days': 90,
                'price_bdt': Decimal('1299.00'),
                'max_businesses': 3,
                'max_cashbooks_per_business': 10,
                'max_transactions': 0,
                'features_list': "Up to 3 Businesses / Branches\n10 Cashbooks per Business\nUnlimited Transactions\nDedicated Tenant DB Isolation\nPriority bKash Approvals\nCustom Date-Range Reports",
                'is_active': True,
                'is_popular': True,
            },
            {
                'name': 'Enterprise Plan',
                'slug': 'enterprise-plan',
                'description': 'Full power for holding companies, trading firms, and multi-branch chains.',
                'billing_cycle': BillingCycle.YEARLY,
                'duration_days': 365,
                'price_bdt': Decimal('3999.00'),
                'max_businesses': 10,
                'max_cashbooks_per_business': 50,
                'max_transactions': 0,
                'features_list': "Up to 10 Businesses / Subsidiaries\n50 Cashbooks per Business\nUnlimited Transactions\nIsolated PostgreSQL Tenant Database\nREST API Mobile Companion Access\nDedicated Account Manager Support",
                'is_active': True,
                'is_popular': False,
            },
        ]

        created_plans = {}
        for p in plans_data:
            plan, _ = SubscriptionPlan.objects.update_or_create(
                slug=p['slug'],
                defaults=p
            )
            created_plans[p['slug']] = plan
            self.stdout.write(f"Plan ready: {plan.name} (BDT {plan.price_bdt})")

        # 3. Demo Service Admin
        demo_user, u_created = User.objects.get_or_create(
            username='demo_owner',
            defaults={
                'email': 'owner@dhakatrading.com',
                'first_name': 'Tanvir',
                'last_name': 'Hasan',
                'business_name': 'Dhaka General Trading Co.',
                'phone_number': '01711223344',
                'role': UserRole.SERVICE_ADMIN,
                'status': AccountStatus.ACTIVE,
            }
        )
        if u_created:
            demo_user.set_password('Password@123')
            demo_user.save()
            self.stdout.write(self.style.SUCCESS("Created Demo Service Admin: demo_owner / Password@123"))

        # 4. Subscription & Approved Payment for Demo User
        growth_plan = created_plans['growth-plan']
        now = timezone.now()
        sub, _ = Subscription.objects.update_or_create(
            user=demo_user,
            defaults={
                'plan': growth_plan,
                'status': SubscriptionStatus.ACTIVE,
                'start_date': now - timedelta(days=5),
                'end_date': now + timedelta(days=85),
                'grace_period_days': 7,
            }
        )

        payment, _ = Payment.objects.get_or_create(
            bkash_transaction_id='9J4K2L8A10',
            defaults={
                'service_admin': demo_user,
                'plan': growth_plan,
                'amount_bdt': growth_plan.price_bdt,
                'sender_bkash_number': '01711223344',
                'status': PaymentStatus.APPROVED,
                'approval_date': now - timedelta(days=5),
                'approved_by': super_admin,
                'admin_notes': 'Verified payment via bKash merchant portal.',
            }
        )

        # 5. Provision Dedicated Tenant Database
        self.stdout.write("Provisioning isolated tenant database for demo_owner...")
        try:
            tenant = provision_tenant_database(demo_user, actor=super_admin)
            self.stdout.write(self.style.SUCCESS(f"Tenant provisioned: {tenant.tenant_id} -> {tenant.db_name}"))

            # 6. Seed Business, Cashbooks, and Transactions inside Tenant Database
            alias = ensure_tenant_database_registered(tenant)
            set_current_tenant_alias(alias)

            from businesses.models import Business
            from cashbooks.models import Cashbook
            from transactions.models import Transaction, TransactionType

            # Business
            biz, _ = Business.objects.get_or_create(
                name='Dhaka General Trading Co.',
                defaults={
                    'address': 'House 14, Road 7, Dhanmondi, Dhaka',
                    'phone': '01711223344',
                    'email': 'contact@dhakatrading.com',
                    'description': 'Main wholesale and retail distribution center.',
                    'opening_balance': Decimal('50000.00'),
                }
            )

            # Cashbooks
            cb1, _ = Cashbook.objects.get_or_create(
                business=biz,
                name='Daily Cash Counter',
                defaults={
                    'opening_balance': Decimal('15000.00'),
                    'description': 'Front-desk retail counter cash collection.',
                }
            )

            cb2, _ = Cashbook.objects.get_or_create(
                business=biz,
                name='Petty Cash Box',
                defaults={
                    'opening_balance': Decimal('5000.00'),
                    'description': 'Daily tea, snacks, courier, and miscellaneous office expenses.',
                }
            )

            cb3, _ = Cashbook.objects.get_or_create(
                business=biz,
                name='City Bank Current Account',
                defaults={
                    'opening_balance': Decimal('30000.00'),
                    'description': 'Operating banking account for vendor transfers.',
                }
            )

            # Sample Transactions (only seed if empty)
            if Transaction.objects.count() == 0:
                sample_transactions = [
                    (cb1, TransactionType.CASH_IN, Decimal('25400.00'), now.date() - timedelta(days=4), 'Sales Revenue', 'Daily retail showroom cash collections', 'MEMO-1001'),
                    (cb1, TransactionType.CASH_IN, Decimal('18500.00'), now.date() - timedelta(days=3), 'Customer Payment', 'Received from Green Enterprise Ltd.', 'INV-402'),
                    (cb1, TransactionType.CASH_OUT, Decimal('15000.00'), now.date() - timedelta(days=3), 'Office Rent', 'Monthly shop front space lease payment', 'RENT-NOV'),
                    (cb2, TransactionType.CASH_OUT, Decimal('1250.00'), now.date() - timedelta(days=2), 'Staff Refreshment', 'Staff tea, snacks & client entertainment', 'VOUCH-012'),
                    (cb2, TransactionType.CASH_OUT, Decimal('850.00'), now.date() - timedelta(days=2), 'Courier & Shipping', 'Sample parcel dispatch via Sundarban Courier', 'SND-981'),
                    (cb3, TransactionType.CASH_IN, Decimal('42000.00'), now.date() - timedelta(days=1), 'Wholesale Sales', 'Cheque deposit from Chittagong wholesale client', 'CHQ-8821'),
                    (cb3, TransactionType.CASH_OUT, Decimal('28000.00'), now.date() - timedelta(days=1), 'Inventory Purchase', 'Supplier payment for electronics stock replenishment', 'SUP-2026'),
                    (cb1, TransactionType.CASH_IN, Decimal('14200.00'), now.date(), 'Counter Sales', 'Morning cash counter sales collection', 'MEMO-1002'),
                ]

                for cb, t_type, amount, dt, cat, desc, ref in sample_transactions:
                    Transaction.objects.create(
                        cashbook=cb,
                        transaction_type=t_type,
                        amount=amount,
                        date=dt,
                        category=cat,
                        description=desc,
                        reference_number=ref,
                    )

                self.stdout.write(self.style.SUCCESS(f"Seeded {len(sample_transactions)} sample transactions in tenant DB."))

            clear_current_tenant_alias()

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Tenant provisioning note: {e}"))
            clear_current_tenant_alias()

        self.stdout.write(self.style.SUCCESS("Data seeding completed successfully!"))
