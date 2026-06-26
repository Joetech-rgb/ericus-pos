from django import forms
from .models import StockAudit, StockAuditItem


class StockAdjustmentForm(forms.Form):
    """
    Manual stock adjustment form.
    Owner/attendant (with PIN) can add or remove units with a written reason.
    """
    DIRECTION_CHOICES = [
        ('in',  'Add Stock (Incoming)'),
        ('out', 'Remove Stock (Outgoing)'),
    ]

    REASON_IN = [
        ('adjustment_in',  'Manual Adjustment (found extra units)'),
        ('initial',        'Initial Stock Entry'),
        ('return',         'Customer Return (no original sale)'),
    ]

    REASON_OUT = [
        ('adjustment_out', 'Manual Adjustment (missing units)'),
        ('damaged',        'Damaged / Written Off'),
    ]

    product_id = forms.IntegerField(widget=forms.HiddenInput())
    direction = forms.ChoiceField(
        choices=DIRECTION_CHOICES,
        widget=forms.RadioSelect(),
        initial='in',
    )
    quantity = forms.IntegerField(
        min_value=1,
        label="Quantity",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 5',
            'min': '1',
        }),
    )
    reason = forms.ChoiceField(
        choices=REASON_IN + REASON_OUT,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    serial_number = forms.CharField(
        max_length=100,
        required=False,
        label="Serial Number (optional)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Serial number if applicable',
        }),
    )
    note = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Required: explain why this stock adjustment is needed',
        }),
        label="Reason / Notes",
        min_length=10,
        error_messages={
            'min_length': 'Please provide at least 10 characters explaining this adjustment.'
        },
    )

    def clean(self):
        cleaned = super().clean()
        direction = cleaned.get('direction')
        reason = cleaned.get('reason')

        in_reasons = {r[0] for r in self.REASON_IN}
        out_reasons = {r[0] for r in self.REASON_OUT}

        if direction == 'in' and reason in out_reasons:
            self.add_error('reason', 'Select an appropriate reason for adding stock.')
        if direction == 'out' and reason in in_reasons:
            self.add_error('reason', 'Select an appropriate reason for removing stock.')
        return cleaned

    def movement_type(self):
        """Returns the correct StockMovement type from the selected reason."""
        return self.cleaned_data.get('reason', 'adjustment_in')


class StockAuditForm(forms.ModelForm):
    """Create a new stock audit session."""
    class Meta:
        model = StockAudit
        fields = ['notes']
        widgets = {
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Optional notes about this stock count (e.g. month-end audit)',
            }),
        }


class StockAuditItemForm(forms.ModelForm):
    """Record the physical count for one product in an audit."""
    class Meta:
        model = StockAuditItem
        fields = ['physical_count', 'notes']
        widgets = {
            'physical_count': forms.NumberInput(attrs={
                'class': 'form-control form-control-sm',
                'min': '0',
            }),
            'notes': forms.TextInput(attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'Optional note',
            }),
        }

    def clean_physical_count(self):
        val = self.cleaned_data['physical_count']
        if val < 0:
            raise forms.ValidationError("Physical count cannot be negative.")
        return val


class DemoUnitForm(forms.Form):
    """Convert a unit to floor display."""
    product_unit_id = forms.IntegerField(widget=forms.HiddenInput())
    condition_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Condition of this unit before putting on display (optional)',
        }),
        label="Condition Notes",
    )


class ReturnDemoForm(forms.Form):
    """Return a demo unit back to sellable stock."""
    demo_unit_id = forms.IntegerField(widget=forms.HiddenInput())
    note = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Reason for returning to stock (optional)',
        }),
        label="Note",
    )


class StockSearchForm(forms.Form):
    """Filter form for the stock dashboard."""
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by product name, brand, or SKU…',
        }),
    )
    category = forms.IntegerField(
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    status = forms.ChoiceField(
        required=False,
        choices=[
            ('',    'All Products'),
            ('low', 'Low Stock'),
            ('out', 'Out of Stock'),
            ('ok',  'In Stock'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
    )