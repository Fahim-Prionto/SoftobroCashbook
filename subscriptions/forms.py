from django import forms
from django.utils.text import slugify
from subscriptions.models import SubscriptionPlan


class SubscriptionPlanForm(forms.ModelForm):
    class Meta:
        model = SubscriptionPlan
        fields = [
            'name',
            'slug',
            'description',
            'billing_cycle',
            'duration_days',
            'price_bdt',
            'max_businesses',
            'max_cashbooks_per_business',
            'max_transactions',
            'features_list',
            'is_active',
            'is_popular',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Professional Business Plan'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. professional-plan'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'billing_cycle': forms.Select(attrs={'class': 'form-select'}),
            'duration_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'price_bdt': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'max_businesses': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_cashbooks_per_business': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_transactions': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0 for unlimited'}),
            'features_list': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'One feature per line...'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_popular': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_slug(self):
        slug = self.cleaned_data.get('slug')
        if not slug:
            name = self.cleaned_data.get('name', '')
            slug = slugify(name)
        return slug

