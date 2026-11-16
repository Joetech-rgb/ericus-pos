from django import forms
from .models import Supplier, PurchaseOrder, PurchaseOrderItem, GoodsReceivedNote, GRNItem
from products.models import Product


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = [
            'name', 'contact_person', 'phone', 'alternate_phone',
            'email', 'address', 'city', 'notes', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'e.g. LG Ghana Ltd'}),
            'contact_person': forms.TextInput(attrs={'placeholder': 'Sales rep name'}),
            'phone': forms.TextInput(attrs={'placeholder': '0241234567'}),
            'alternate_phone': forms.TextInput(attrs={'placeholder': '0301234567'}),
            'email': forms.EmailInput(attrs={'placeholder': 'supplier@example.com'}),
            'address': forms.Textarea(attrs={'rows': 2}),
            'city': forms.TextInput(attrs={'placeholder': 'e.g. Accra'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Payment terms, lead times, etc.'}),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '')
        if phone and not phone.replace('+', '').replace(' ', '').isdigit():
            raise forms.ValidationError("Enter a valid phone number.")
        return phone


class PurchaseOrderForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrder
        fields = [
            'supplier', 'order_date', 'expected_date',
            'discount_amount', 'tax_amount', 'shipping_cost',
            'payment_method', 'payment_reference', 'notes', 'internal_notes'
        ]
        widgets = {
            'order_date': forms.DateInput(attrs={'type': 'date'}),
            'expected_date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Notes visible to supplier'}),
            'internal_notes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Internal notes (owner only)'}),
            'discount_amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'tax_amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'shipping_cost': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['supplier'].queryset = Supplier.objects.filter(is_active=True)
        self.fields['expected_date'].required = False
        self.fields['payment_method'].required = False
        self.fields['payment_reference'].required = False
        for _f in ('discount_amount', 'tax_amount', 'shipping_cost', 'order_date'):
            self.fields[_f].required = False
        from django.utils import timezone
        self.fields['order_date'].initial = timezone.localdate()

    def clean(self):
        cleaned_data = super().clean()
        discount = cleaned_data.get('discount_amount', 0) or 0
        tax = cleaned_data.get('tax_amount', 0) or 0
        shipping = cleaned_data.get('shipping_cost', 0) or 0
        cleaned_data['discount_amount'] = discount
        cleaned_data['tax_amount'] = tax
        cleaned_data['shipping_cost'] = shipping
        if not cleaned_data.get('order_date'):
            from django.utils import timezone
            cleaned_data['order_date'] = timezone.localdate()
        if discount < 0:
            self.add_error('discount_amount', 'Discount cannot be negative.')
        if tax < 0:
            self.add_error('tax_amount', 'Tax cannot be negative.')
        if shipping < 0:
            self.add_error('shipping_cost', 'Shipping cost cannot be negative.')
        return cleaned_data


class PurchaseOrderItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseOrderItem
        fields = ['product', 'quantity_ordered', 'unit_cost', 'notes']
        widgets = {
            'quantity_ordered': forms.NumberInput(attrs={'min': '1', 'step': '1'}),
            'unit_cost': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01', 'placeholder': '0.00'}),
            'notes': forms.TextInput(attrs={'placeholder': 'Optional note for this line'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.filter(
            is_active=True
        ).select_related('category').order_by('name')
        self.fields['notes'].required = False

    def clean_quantity_ordered(self):
        qty = self.cleaned_data.get('quantity_ordered')
        if qty is not None and qty < 1:
            raise forms.ValidationError("Quantity must be at least 1.")
        return qty

    def clean_unit_cost(self):
        cost = self.cleaned_data.get('unit_cost')
        if cost is not None and cost <= 0:
            raise forms.ValidationError("Unit cost must be greater than zero.")
        return cost


PurchaseOrderItemFormSet = forms.inlineformset_factory(
    PurchaseOrder,
    PurchaseOrderItem,
    form=PurchaseOrderItemForm,
    extra=3,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


class GRNForm(forms.ModelForm):
    class Meta:
        model = GoodsReceivedNote
        fields = ['received_date', 'delivery_note_number', 'notes']
        widgets = {
            'received_date': forms.DateInput(attrs={'type': 'date'}),
            'delivery_note_number': forms.TextInput(attrs={'placeholder': 'Supplier delivery note/waybill number'}),
            'notes': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Any issues, damages, notes about this delivery'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['delivery_note_number'].required = False
        self.fields['notes'].required = False


class GRNItemForm(forms.Form):
    """Dynamic form for each PO item during GRN."""
    po_item_id = forms.IntegerField(widget=forms.HiddenInput)
    quantity_received = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={'min': '0', 'step': '1'})
    )
    condition = forms.ChoiceField(choices=[
        ('new', 'New / Good'),
        ('damaged', 'Damaged'),
    ])
    notes = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Optional note'})
    )


class PaymentUpdateForm(forms.ModelForm):
    """Lets owner record a payment against an existing PO."""
    class Meta:
        model = PurchaseOrder
        fields = ['amount_paid', 'payment_method', 'payment_reference']
        widgets = {
            'amount_paid': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'payment_reference': forms.TextInput(attrs={'placeholder': 'MoMo ID / Bank ref / Cheque no.'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['payment_method'].required = True
        self.fields['payment_reference'].required = False

    def clean_amount_paid(self):
        amount = self.cleaned_data.get('amount_paid')
        if amount is not None and amount < 0:
            raise forms.ValidationError("Payment amount cannot be negative.")
        return amount