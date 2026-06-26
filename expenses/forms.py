from django import forms
from .models import Expense, ExpenseCategory


class ExpenseCategoryForm(forms.ModelForm):
    class Meta:
        model  = ExpenseCategory
        fields = ['name', 'description', 'icon', 'is_active']
        widgets = {
            'name':        forms.TextInput(attrs={'placeholder': 'e.g. Utilities'}),
            'description': forms.Textarea(attrs={'rows': 2}),
            'icon':        forms.TextInput(attrs={'placeholder': 'fa-bolt'}),
        }


class ExpenseForm(forms.ModelForm):
    class Meta:
        model  = Expense
        fields = [
            'category', 'title', 'amount', 'payment_method',
            'reference', 'expense_date', 'notes', 'receipt_image',
            'is_recurring', 'recurrence_note',
        ]
        widgets = {
            'title':           forms.TextInput(attrs={'placeholder': 'e.g. Monthly rent — May 2026'}),
            'amount':          forms.NumberInput(attrs={'min': 0.01, 'step': '0.01'}),
            'payment_method':  forms.Select(),
            'reference':       forms.TextInput(attrs={'placeholder': 'MoMo ID / bank ref (optional)'}),
            'expense_date':    forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'notes':           forms.Textarea(attrs={'rows': 2}),
            'recurrence_note': forms.TextInput(attrs={'placeholder': 'e.g. Every 1st of the month'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = ExpenseCategory.objects.filter(is_active=True)
        # Pre-format date field
        if self.instance and self.instance.pk and self.instance.expense_date:
            self.initial['expense_date'] = self.instance.expense_date.strftime('%Y-%m-%d')

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if amount <= 0:
            raise forms.ValidationError('Amount must be greater than zero.')
        return amount


class ExpenseRejectForm(forms.Form):
    reason = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Reason for rejection…'}),
        label='Rejection Reason',
        required=False,
    )