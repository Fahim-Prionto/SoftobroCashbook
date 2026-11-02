from django.test import TestCase
from accounts.models import User, UserRole, AccountStatus


class AccountsModelTests(TestCase):
    def test_create_service_admin(self):
        user = User.objects.create_user(
            username='shop_owner',
            email='owner@test.com',
            password='Password@123',
            role=UserRole.SERVICE_ADMIN,
            business_name='Test Shop Ltd',
            phone_number='01700000001',
        )
        self.assertTrue(user.is_service_admin)
        self.assertFalse(user.is_super_admin)
        self.assertEqual(user.status, AccountStatus.PENDING_APPROVAL)
        self.assertFalse(user.is_approved)

    def test_create_super_admin(self):
        admin = User.objects.create_user(
            username='admin_user',
            email='admin@test.com',
            password='Password@123',
            role=UserRole.SUPER_ADMIN,
            status=AccountStatus.ACTIVE,
        )
        self.assertTrue(admin.is_super_admin)
        self.assertFalse(admin.is_service_admin)
        self.assertTrue(admin.is_approved)
