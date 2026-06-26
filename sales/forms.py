"""
sales/forms.py
"""
from decimal import Decimal
from django import forms


class CheckoutForm(forms.Form):
    """
    Final payment form submitted when completing a sale.
    Handles all four payment methods.
    """
    PAYMENT_METHOD_CHOICES = [
        ('cash',   'Cash'),
        ('momo',   'Mobile Money (MoMo)'),
        ('split',  'Split — Cash + MoMo'),
        ('credit', 'Credit'),
    ]

    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHOD_CHOICES,
        widget=forms.RadioSelect(),
    )
    cash_tendered = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01',
        }),
        label="Cash Amount",
    )
    momo_amount = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01',
        }),
        label="MoMo Amount",
    )
    momo_reference = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'MoMo transaction ID',
        }),
        label="MoMo Reference",
    )
    credit_due_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
        }),
        label="Due Date",
    )
    installation_fee = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01',
        }),
        label="Installation Fee (GH₵)",
    )
    delivery_fee = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01',
        }),
        label="Delivery Fee (GH₵)",
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Any notes for this sale…',
        }),
    )
    customer_id = forms.IntegerField(required=False, widget=forms.HiddenInput())
    sale_type = forms.ChoiceField(
        choices=[('retail', 'Retail'), ('wholesale', 'Wholesale')],
        initial='retail',
        widget=forms.HiddenInput(),
    )
    discount_code = forms.CharField(
        required=False,
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-control text-uppercase',
            'placeholder': 'Promo code (optional)',
        }),
    )

    def clean(self):
        cleaned = super().clean()
        method = cleaned.get('payment_method')
        cash = cleaned.get('cash_tendered') or Decimal('0')
        momo = cleaned.get('momo_amount') or Decimal('0')

        # MoMo reference is only required when payment method is momo or split
        if method in ('momo', 'split') and not cleaned.get('momo_reference'):
            self.add_error('momo_reference', 'MoMo reference number is required.')

        if method == 'split':
            if cash <= 0 and momo <= 0:
                raise forms.ValidationError(
                    "For split payment, enter at least one of cash or MoMo amount."
                )

        if method == 'credit' and not cleaned.get('credit_due_date'):
            self.add_error('credit_due_date', 'Due date is required for credit sales.')

        cleaned['cash_tendered'] = cash
        cleaned['momo_amount'] = momo
        return cleaned


class AddToCartForm(forms.Form):
    """Submitted when adding a product to the cart."""
    product_id = forms.IntegerField()
    product_unit_id = forms.IntegerField(required=False)
    quantity = forms.IntegerField(min_value=1, initial=1)
    unit_price = forms.DecimalField(required=False, min_value=0, decimal_places=2)


class UpdateCartItemForm(forms.Form):
    product_id = forms.IntegerField()
    product_unit_id = forms.IntegerField(required=False)
    quantity = forms.IntegerField(min_value=0)  # 0 = remove


class ApplyDiscountForm(forms.Form):
    code = forms.CharField(max_length=50)

    def clean_code(self):
        return self.cleaned_data['code'].strip().upper()


class SaleFilterForm(forms.Form):
    """Filter the sale history list."""
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Receipt number, customer, attendant…',
        }),
    )
    payment_method = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All Methods'),
            ('cash', 'Cash'),
            ('momo', 'Mobile Money'),
            ('split', 'Split'),
            ('credit', 'Credit'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
    )
    attendant_id = forms.IntegerField(required=False, widget=forms.HiddenInput())