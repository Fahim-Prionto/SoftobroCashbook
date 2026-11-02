from django.test import TestCase
from accounts.models import User, UserRole, AccountStatus
from tenants.models import Tenant, TenantStatus
from tenants.context import set_current_tenant_alias, get_current_tenant_alias, clear_current_tenant_alias
from tenants.router import TenantDatabaseRouter


class TenantIsolationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='tenant_tester',
            email='tester@test.com',
            password='Password@123',
            role=UserRole.SERVICE_ADMIN,
            status=AccountStatus.ACTIVE,
        )
        self.tenant = Tenant.objects.create(
            service_admin=self.user,
            tenant_id='tenant_999',
            db_name='scb_tenant_999',
            db_user='postgres',
            status=TenantStatus.PROVISIONED,
        )
        self.tenant.set_db_password('super_secret_db_password')
        self.tenant.save()

    def test_tenant_password_encryption_and_decryption(self):
        self.tenant.refresh_from_db()
        # Ensure raw password is NOT stored as plaintext
        self.assertNotEqual(self.tenant.db_password_encrypted, 'super_secret_db_password')
        # Ensure decryption returns original plaintext
        self.assertEqual(self.tenant.get_db_password(), 'super_secret_db_password')

    def test_tenant_context_thread_locals(self):
        clear_current_tenant_alias()
        self.assertIsNone(get_current_tenant_alias())

        set_current_tenant_alias('tenant_999')
        self.assertEqual(get_current_tenant_alias(), 'tenant_999')

        clear_current_tenant_alias()
        self.assertIsNone(get_current_tenant_alias())

    def test_tenant_database_router(self):
        router = TenantDatabaseRouter()
        from accounts.models import User
        from businesses.models import Business

        # Central app model User always routes to default
        self.assertEqual(router.db_for_read(User), 'default')
        self.assertEqual(router.db_for_write(User), 'default')

        # Tenant app model Business routes to thread-local tenant alias when set
        set_current_tenant_alias('tenant_999')
        self.assertEqual(router.db_for_read(Business), 'tenant_999')
        self.assertEqual(router.db_for_write(Business), 'tenant_999')

        clear_current_tenant_alias()
        self.assertEqual(router.db_for_read(Business), 'default')
