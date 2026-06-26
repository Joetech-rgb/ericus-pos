from django import forms
from .models import Discount


class DiscountForm(forms.ModelForm):
    class Meta:
        model  = Discount
        fields = [
            'name', 'code', 'description',
            'discount_type', 'scope', 'customer_target',
            'value', 'buy_quantity', 'get_quantity',
            'minimum_amount', 'maximum_discount',
            'products', 'categories',
            'valid_from', 'valid_until',
            'usage_limit', 'usage_limit_per_customer',
            'is_active', 'requires_pin', 'is_automatic',
        ]
        widgets = {
            'name':                   forms.TextInput(attrs={'placeholder': 'e.g. End-of-Year Sale'}),
            'code':                   forms.TextInput(attrs={'placeholder': 'e.g. SAVE20 (optional)'}),
            'description':            forms.Textarea(attrs={'rows': 2}),
            'value':                  forms.NumberInput(attrs={'min': 0, 'step': '0.01'}),
            'minimum_amount':         forms.NumberInput(attrs={'min': 0, 'step': '0.01'}),
            'maximum_discount':       forms.NumberInput(attrs={'min': 0, 'step': '0.01'}),
            'buy_quantity':           forms.NumberInput(attrs={'min': 1}),
            'get_quantity':           forms.NumberInput(attrs={'min': 1}),
            'usage_limit':            forms.NumberInput(attrs={'min': 0}),
            'usage_limit_per_customer': forms.NumberInput(attrs={'min': 0}),
            'valid_from':             forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'valid_until':            forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'products':               forms.CheckboxSelectMultiple(),
            'categories':             forms.CheckboxSelectMultiple(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-format datetime fields for the datetime-local input
        if self.instance and self.instance.pk:
            if self.instance.valid_from:
                self.initial['valid_from'] = self.instance.valid_from.strftime('%Y-%m-%dT%H:%M')
            if self.instance.valid_until:
                self.initial['valid_until'] = self.instance.valid_until.strftime('%Y-%m-%dT%H:%M')

    def clean(self):
        cleaned = super().clean()
        dtype  = cleaned.get('discount_type')
        value  = cleaned.get('value', 0)
        scope  = cleaned.get('scope')
        vfrom  = cleaned.get('valid_from')
        vuntil = cleaned.get('valid_until')

        if dtype == Discount.TYPE_PERCENTAGE:
            if not (0 < value <= 100):
                self.add_error('value', 'Percentage must be between 1 and 100.')

        if dtype == Discount.TYPE_FIXED:
            if value <= 0:
                self.add_error('value', 'Fixed discount amount must be greater than zero.')

        if scope == Discount.SCOPE_PRODUCT and not cleaned.get('products'):
            self.add_error('products', 'Select at least one product for a product-scoped discount.')

        if scope == Discount.SCOPE_CATEGORY and not cleaned.get('categories'):
            self.add_error('categories', 'Select at least one category for a category-scoped discount.')

        if vfrom and vuntil and vuntil <= vfrom:
            self.add_error('valid_until', 'Expiry date must be after the start date.')

        return cleaned


class ApplyDiscountForm(forms.Form):
    """Used on the POS to enter a promo code."""
    code = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'placeholder': 'Enter promo code…', 'autocomplete': 'off'}),
        label='Promo Code',
    )

    def clean_code(self):
        return self.cleaned_data['code'].strip().upper()