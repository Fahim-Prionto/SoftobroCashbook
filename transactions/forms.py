from django import forms
from django.utils import timezone
from transactions.models import Transaction, TransactionType

COMMON_IN_CATEGORIES = [
    'Sales Revenue',
    'Customer Payment',
    'Capital Investment',
    'Bank Withdrawal',
    'Loan Received',
    'Asset Sale',
    'Refund Received',
    'Other Cash-In',
]

COMMON_OUT_CATEGORIES = [
    'Inventory / Supplies Purchase',
    'Staff Salary & Wages',
    'Office / Shop Rent',
    'Electricity & Utilities',
    'Transportation & Fuel',
    'Marketing & Advertising',
    'Maintenance & Repair',
    'Bank Deposit',
    'Loan Repayment',
    'Owner Drawings / Personal',
    'Other Cash-Out',
]


class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = [
            'transaction_type',
            'amount',
            'date',
            'category',
            'description',
            'reference_number',
            'attachment',
        ]
        widgets = {
            'transaction_type': forms.Select(attrs={'class': 'form-select form-select-lg'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control form-control-lg', 'step': '0.01', 'placeholder': '0.00'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'category': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Sales Revenue, Salary, Rent'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Details or notes...'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Voucher, Memo, or Inv #'}),
            'attachment': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.initial.get('date'):
            self.initial['date'] = timezone.now().date()

