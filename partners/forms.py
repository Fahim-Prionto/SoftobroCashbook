from django import forms
from .models import Partner, PartnerType


class PartnerForm(forms.ModelForm):
    """Form for creating and editing a Partner (Customer/Vendor)."""

    class Meta:
        model = Partner
        fields = ['name', 'partner_type', 'phone', 'email', 'address', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Partner / Company name',
            }),
            'partner_type': forms.Select(attrs={
                'class': 'form-select',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+880 1XXXXXXXXX',
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@example.com',
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Full address (optional)',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Internal notes (optional)',
            }),
        }

