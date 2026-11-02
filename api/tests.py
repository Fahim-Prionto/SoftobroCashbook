from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from accounts.models import User, UserRole, AccountStatus
from businesses.models import Business
from cashbooks.models import Cashbook
from transactions.models import Transaction, TransactionType


class RestApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='api_merchant',
            email='api@test.com',
            password='Password@123',
            role=UserRole.SERVICE_ADMIN,
            status=AccountStatus.ACTIVE,
        )

    def test_api_login(self):
        url = reverse('api:api_login')
        response = self.client.post(url, {
            'username': 'api_merchant',
            'password': 'Password@123',
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertEqual(response.data['user']['username'], 'api_merchant')

    def test_api_businesses_crud(self):
        self.client.force_authenticate(user=self.user)

        # Create Business
        url = reverse('api:business-list')
        response = self.client.post(url, {
            'name': 'API Branch 1',
            'opening_balance': '10000.00',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        biz_id = response.data['id']

        # List Businesses
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

        # Create Cashbook
        cb_url = reverse('api:cashbook-list')
        cb_resp = self.client.post(cb_url, {
            'business': biz_id,
            'name': 'API Cash Drawer',
            'opening_balance': '2000.00',
        }, format='json')
        self.assertEqual(cb_resp.status_code, status.HTTP_201_CREATED)
        cb_id = cb_resp.data['id']

        # Create Transaction
        t_url = reverse('api:transaction-list')
        t_resp = self.client.post(t_url, {
            'cashbook': cb_id,
            'transaction_type': 'CASH_IN',
            'amount': '5000.00',
            'date': '2026-11-02',
            'category': 'Sales',
        }, format='json')
        self.assertEqual(t_resp.status_code, status.HTTP_201_CREATED)

        # Financial Summary API
        summary_url = reverse('api:api_summary')
        sum_resp = self.client.get(summary_url)
        self.assertEqual(sum_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(sum_resp.data['total_businesses'], 1)
        self.assertEqual(sum_resp.data['total_cashbooks'], 1)
