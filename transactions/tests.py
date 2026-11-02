from decimal import Decimal
from django.test import TestCase
from django.utils import timezone
from businesses.models import Business
from cashbooks.models import Cashbook
from transactions.models import Transaction, TransactionType


class FinancialCalculationTests(TestCase):
    def setUp(self):
        self.business = Business.objects.create(
            name='Test Financial Firm',
            opening_balance=Decimal('20000.00'),
        )
        self.cashbook1 = Cashbook.objects.create(
            business=self.business,
            name='Counter Cash',
            opening_balance=Decimal('5000.00'),
        )
        self.cashbook2 = Cashbook.objects.create(
            business=self.business,
            name='Bank Cash',
            opening_balance=Decimal('10000.00'),
        )

    def test_cashbook_and_business_balance_calculations(self):
        today = timezone.now().date()

        # Inflows
        Transaction.objects.create(
            cashbook=self.cashbook1,
            transaction_type=TransactionType.CASH_IN,
            amount=Decimal('12500.50'),
            date=today,
            category='Sales',
        )
        Transaction.objects.create(
            cashbook=self.cashbook1,
            transaction_type=TransactionType.CASH_OUT,
            amount=Decimal('4200.25'),
            date=today,
            category='Rent',
        )

        # Cashbook 1: 5000.00 + 12500.50 - 4200.25 = 13300.25
        self.assertEqual(self.cashbook1.get_total_cash_in(), Decimal('12500.50'))
        self.assertEqual(self.cashbook1.get_total_cash_out(), Decimal('4200.25'))
        self.assertEqual(self.cashbook1.get_current_balance(), Decimal('13300.25'))

        # Add to Cashbook 2: Inflow 8000.00
        Transaction.objects.create(
            cashbook=self.cashbook2,
            transaction_type=TransactionType.CASH_IN,
            amount=Decimal('8000.00'),
            date=today,
            category='Investment',
        )
        # Cashbook 2: 10000.00 + 8000.00 = 18000.00
        self.assertEqual(self.cashbook2.get_current_balance(), Decimal('18000.00'))

        # Total business balance:
        # Business opening (20000) + CB1 opening (5000) + CB2 opening (10000) + Total IN (20500.50) - Total OUT (4200.25)
        # = 35000 + 20500.50 - 4200.25 = 51300.25
        self.assertEqual(self.business.get_total_cash_in(), Decimal('20500.50'))
        self.assertEqual(self.business.get_total_cash_out(), Decimal('4200.25'))
        self.assertEqual(self.business.get_current_balance(), Decimal('51300.25'))
