from django import forms
from .models import WholesaleOrder, WholesaleOrderItem
from products.models import Product


class WholesaleOrderForm(forms.ModelForm):
    class Meta:
        model = WholesaleOrder
        fields = [
            'customer', 'order_date', 'delivery_date', 'delivery_address',
            'discount_amount', 'delivery_fee', 'payment_method',
            'payment_reference', 'notes',
        ]
        widgets = {
            'order_date': forms.DateInput(attrs={'type': 'date'}),
            'delivery_date': forms.DateInput(attrs={'type': 'date'}),
            'delivery_address': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 2}),
            'discount_amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'delivery_fee': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from customers.models import Customer
        self.fields['customer'].queryset = Customer.objects.filter(
            customer_type='wholesale', is_active=True
        ).order_by('full_name')
        self.fields['delivery_date'].required = False
        self.fields['delivery_address'].required = False
        self.fields['payment_method'].required = False
        self.fields['payment_reference'].required = False
        self.fields['notes'].required = False


class WholesaleOrderItemForm(forms.ModelForm):
    class Meta:
        model = WholesaleOrderItem
        fields = ['product', 'quantity', 'unit_price', 'notes']
        widgets = {
            'quantity': forms.NumberInput(attrs={'min': '1', 'step': '1'}),
            'unit_price': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
            'notes': forms.TextInput(attrs={'placeholder': 'Optional'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.filter(
            is_active=True
        ).order_by('name')
        self.fields['notes'].required = False

    def clean_quantity(self):
        qty = self.cleaned_data.get('quantity')
        if qty is not None and qty < 1:
            raise forms.ValidationError("Quantity must be at least 1.")
        return qty

    def clean_unit_price(self):
        price = self.cleaned_data.get('unit_price')
        if price is not None and price <= 0:
            raise forms.ValidationError("Unit price must be greater than zero.")
        return price


WholesaleOrderItemFormSet = forms.inlineformset_factory(
    WholesaleOrder,
    WholesaleOrderItem,
    form=WholesaleOrderItemForm,
    extra=3,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class WholesalePaymentForm(forms.ModelForm):
    class Meta:
        model = WholesaleOrder
        fields = ['amount_paid', 'payment_method', 'payment_reference']
        widgets = {
            'amount_paid': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'payment_reference': forms.TextInput(attrs={'placeholder': 'MoMo ID / Bank ref / Cheque no.'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['payment_method'].required = True
        self.fields['payment_reference'].required = False
