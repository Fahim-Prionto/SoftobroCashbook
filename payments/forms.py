from django import forms
from payments.models import Payment, BKashSetting


class ManualBkashPaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['bkash_transaction_id', 'sender_bkash_number', 'payment_screenshot']
        widgets = {
            'bkash_transaction_id': forms.TextInput(
                attrs={
                    'class': 'form-control form-control-lg text-uppercase font-monospace',
                    'placeholder': 'e.g. 9J4K2L8A10',
                    'style': 'letter-spacing: 2px;',
                }
            ),
            'sender_bkash_number': forms.TextInput(
                attrs={
                    'class': 'form-control form-control-lg',
                    'placeholder': '01XXXXXXXXX',
                }
            ),
            'payment_screenshot': forms.FileInput(
                attrs={'class': 'form-control'}
            ),
        }

    def clean_bkash_transaction_id(self):
        trx_id = self.cleaned_data.get('bkash_transaction_id', '').strip().upper()
        if len(trx_id) < 6:
            raise forms.ValidationError("Please enter a valid bKash Transaction ID.")
        if Payment.objects.filter(bkash_transaction_id=trx_id).exists():
            raise forms.ValidationError("This bKash Transaction ID has already been submitted.")
        return trx_id

    def clean_sender_bkash_number(self):
        phone = self.cleaned_data.get('sender_bkash_number', '').strip()
        if not phone.startswith(('01', '+8801', '8801')):
            raise forms.ValidationError("Please provide a valid sender bKash number.")
        return phone


class AdminPaymentVerificationForm(forms.Form):
    action = forms.ChoiceField(
        choices=[('APPROVE', 'Approve Payment & Activate Tenant'), ('REJECT', 'Reject Payment')],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )
    admin_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Optional internal remarks or rejection reason...'}
        )
    )


class BKashSettingForm(forms.ModelForm):
    class Meta:
        model = BKashSetting
        fields = ['company_number', 'account_type', 'instruction_text', 'is_active']
        widgets = {
            'company_number': forms.TextInput(
                attrs={
                    'class': 'form-control form-control-lg font-monospace fw-bold',
                    'placeholder': 'e.g. 01712345678',
                }
            ),
            'account_type': forms.Select(
                attrs={
                    'class': 'form-select form-select-lg',
                }
            ),
            'instruction_text': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Instructions shown to customers during bKash payment...',
                }
            ),
            'is_active': forms.CheckboxInput(
                attrs={
                    'class': 'form-check-input',
                }
            ),
        }

    def clean_company_number(self):
        number = self.cleaned_data.get('company_number', '').strip()
        if not number:
            raise forms.ValidationError("bKash company number cannot be empty.")
        return number


