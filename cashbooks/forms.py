from django import forms
from cashbooks.models import Cashbook


class CashbookForm(forms.ModelForm):
    class Meta:
        model = Cashbook
        fields = ['name', 'opening_balance', 'description', 'status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Daily Cash Drawer, Petty Cash, City Bank Account'}),
            'opening_balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Purpose of this cashbook...'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

