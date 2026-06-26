from django import forms
from .models import Customer, CreditPayment


class CustomerForm(forms.ModelForm):
    class Meta:
        model  = Customer
        fields = [
            'full_name', 'phone', 'phone_alt', 'email',
            'company_name', 'address', 'customer_type',
            'credit_limit', 'notes',
        ]
        widgets = {
            'full_name':     forms.TextInput(attrs={'placeholder': 'e.g. Kwame Mensah'}),
            'phone':         forms.TextInput(attrs={'placeholder': '0241234567'}),
            'phone_alt':     forms.TextInput(attrs={'placeholder': 'Optional secondary number'}),
            'email':         forms.EmailInput(attrs={'placeholder': 'Optional'}),
            'company_name':  forms.TextInput(attrs={'placeholder': 'Optional — for business customers'}),
            'address':       forms.Textarea(attrs={'rows': 2, 'placeholder': 'Town / area'}),
            'credit_limit':  forms.NumberInput(attrs={'min': 0, 'step': '0.01'}),
            'notes':         forms.Textarea(attrs={'rows': 2}),
            'customer_type': forms.Select(),
        }

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()
        if not phone.replace('+', '').replace(' ', '').isdigit():
            raise forms.ValidationError('Enter a valid phone number.')
        return phone


class CreditPaymentForm(forms.ModelForm):
    class Meta:
        model  = CreditPayment
        fields = ['amount', 'payment_method', 'reference', 'note']
        widgets = {
            'amount':         forms.NumberInput(attrs={'min': 0.01, 'step': '0.01'}),
            'payment_method': forms.Select(),
            'reference':      forms.TextInput(attrs={'placeholder': 'MoMo ID / bank ref (optional)'}),
            'note':           forms.Textarea(attrs={'rows': 2}),
        }

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError('Amount must be greater than zero.')
        return amount


class CustomerSearchForm(forms.Form):
    """Lightweight form used by POS AJAX search."""
    q = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'Search by name or phone…'}),
        required=False,
    )