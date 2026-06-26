from django import forms
from .models import Product, Category, ProductUnit


CSS = 'w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500'


class ProductForm(forms.ModelForm):
    class Meta:
        model  = Product
        fields = [
            'name', 'category', 'brand', 'model_number', 'description',
            'barcode', 'sku', 'cost_price', 'selling_price', 'wholesale_price',
            'warranty_months', 'voltage', 'capacity', 'color',
            'reorder_point', 'track_serials', 'image', 'is_active',
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': CSS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name not in ('description', 'track_serials', 'is_active', 'image'):
                field.widget.attrs['class'] = CSS


class CategoryForm(forms.ModelForm):
    class Meta:
        model  = Category
        fields = ['name', 'icon', 'description', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = CSS


class ProductUnitForm(forms.ModelForm):
    class Meta:
        model  = ProductUnit
        fields = ['serial_number', 'condition', 'purchase_cost', 'notes']

    def __init__(self, *args, **kwargs):
        # ✅ Accept product kwarg so we can validate serial uniqueness
        self.product = kwargs.pop('product', None)
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = CSS

    def clean_serial_number(self):
        serial = self.cleaned_data.get('serial_number', '').strip()

        if serial and self.product:
            qs = ProductUnit.objects.filter(
                product=self.product,
                serial_number=serial,
            )
            # Exclude current instance when editing an existing unit
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise forms.ValidationError(
                    f'Serial number "{serial}" already exists for this product.'
                )

        return serial


class BulkImportForm(forms.Form):
    file = forms.FileField(
        label='Excel File (.xlsx)',
        help_text='Download the template, fill it in, and upload here.',
        widget=forms.FileInput(attrs={'accept': '.xlsx', 'class': CSS})
    )