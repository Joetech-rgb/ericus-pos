from django import forms
from .models import Return


class ReturnCreateForm(forms.ModelForm):
    """Used by attendant or owner to log an incoming return."""

    class Meta:
        model = Return
        fields = [
            'sale', 'sale_item', 'product', 'quantity',
            'serial_number', 'reason', 'reason_detail',
            'condition', 'original_price', 'return_date',
        ]
        widgets = {
            'return_date': forms.DateInput(attrs={'type': 'date'}),
            'reason_detail': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Describe the issue in detail...'
            }),
            'serial_number': forms.TextInput(attrs={'placeholder': 'Serial number if applicable'}),
            'original_price': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'quantity': forms.NumberInput(attrs={'min': '1', 'step': '1'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from sales.models import Sale, SaleItem
        from products.models import Product
        self.fields['sale'].queryset = Sale.objects.select_related('customer').order_by('-created_at')
        self.fields['sale_item'].queryset = SaleItem.objects.none()
        self.fields['sale_item'].required = False
        self.fields['serial_number'].required = False
        self.fields['reason_detail'].required = False

        # If editing and sale is set, populate sale_item queryset
        if self.instance.pk and self.instance.sale_id:
            self.fields['sale_item'].queryset = SaleItem.objects.filter(
                sale=self.instance.sale
            )
        elif self.data.get('sale'):
            try:
                sale_id = int(self.data['sale'])
                self.fields['sale_item'].queryset = SaleItem.objects.filter(sale_id=sale_id)
            except (ValueError, TypeError):
                pass

    def clean_quantity(self):
        qty = self.cleaned_data.get('quantity')
        if qty is not None and qty < 1:
            raise forms.ValidationError("Quantity must be at least 1.")
        return qty

    def clean_original_price(self):
        price = self.cleaned_data.get('original_price')
        if price is not None and price < 0:
            raise forms.ValidationError("Original price cannot be negative.")
        return price


class ReturnResolveForm(forms.ModelForm):
    """Owner resolves an approved return."""

    class Meta:
        model = Return
        fields = [
            'resolution', 'refund_amount', 'restocking_fee',
            'resolution_notes', 'return_to_stock', 'mark_as_damaged',
        ]
        widgets = {
            'resolution_notes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Describe what was done and any notes...'
            }),
            'refund_amount': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'restocking_fee': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['resolution'].required = True
        self.fields['resolution_notes'].required = False
        self.fields['restocking_fee'].required = False

    def clean(self):
        cleaned_data = super().clean()
        refund = cleaned_data.get('refund_amount', 0) or 0
        fee = cleaned_data.get('restocking_fee', 0) or 0
        return_to_stock = cleaned_data.get('return_to_stock')
        mark_damaged = cleaned_data.get('mark_as_damaged')

        if refund < 0:
            self.add_error('refund_amount', 'Refund amount cannot be negative.')
        if fee < 0:
            self.add_error('restocking_fee', 'Restocking fee cannot be negative.')
        if fee > refund:
            self.add_error('restocking_fee', 'Restocking fee cannot exceed refund amount.')
        if return_to_stock and mark_damaged:
            self.add_error('mark_as_damaged', 'Cannot both return to stock and mark as damaged.')
        return cleaned_data


class ReturnRejectForm(forms.Form):
    rejection_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Reason for rejection (optional)'
        }),
        label='Rejection Reason'
    )


class ReturnFilterForm(forms.Form):
    q = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Search return number, product...'}))
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Statuses')] + Return.STATUS_CHOICES
    )
    reason = forms.ChoiceField(
        required=False,
        choices=[('', 'All Reasons')] + Return.REASON_CHOICES
    )
    date_from = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    date_to = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))