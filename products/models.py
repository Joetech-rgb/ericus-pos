from django.db import models
from django.utils import timezone
from django.conf import settings


# ─── Category ─────────────────────────────────────────────────────────────────

class Category(models.Model):
    ICON_CHOICES = [
        ('fridge',       '🧊 Fridges & Freezers'),
        ('tv',           '📺 TVs & Electronics'),
        ('ac',           '❄️ Air Conditioners'),
        ('generator',    '⚡ Generators'),
        ('washing',      '🫧 Washing Machines'),
        ('lighting',     '💡 Lighting'),
        ('small',        '🔌 Small Appliances'),
        ('accessories',  '🔧 Accessories'),
        ('inverter',     '🔋 Inverters & Batteries'),
        ('sound',        '🔊 Sound Systems'),
        ('other',        '📦 Other'),
    ]

    name        = models.CharField(max_length=100, unique=True)
    icon        = models.CharField(max_length=20, choices=ICON_CHOICES, default='other')
    description = models.TextField(blank=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering            = ['name']

    def __str__(self):
        return self.name

    @property
    def product_count(self):
        return self.products.filter(is_active=True).count()


# ─── Product ──────────────────────────────────────────────────────────────────

class Product(models.Model):
    CONDITION_CHOICES = [
        ('new',      'New'),
        ('refurb',   'Refurbished'),
        ('demo',     'Demo Unit'),
    ]

    # Basic Info
    name            = models.CharField(max_length=200)
    category        = models.ForeignKey(Category, on_delete=models.PROTECT,
                                        related_name='products')
    brand           = models.CharField(max_length=100, blank=True)
    model_number    = models.CharField(max_length=100, blank=True)
    description     = models.TextField(blank=True)

    # Identification
    barcode         = models.CharField(max_length=100, blank=True, unique=True, null=True)
    sku             = models.CharField(max_length=100, blank=True, unique=True, null=True)

    # Pricing
    cost_price      = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    selling_price   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    wholesale_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Specs
    warranty_months = models.PositiveIntegerField(default=0,
                        help_text='Warranty period in months. 0 = no warranty.')
    voltage         = models.CharField(max_length=50, blank=True,
                        help_text='e.g. 220V, 110V, 12V')
    capacity        = models.CharField(max_length=100, blank=True,
                        help_text='e.g. 300L, 1.5HP, 5.5kg')
    color           = models.CharField(max_length=50, blank=True)

    # Stock Control
    reorder_point   = models.PositiveIntegerField(default=5,
                        help_text='Alert when stock falls below this level.')
    track_serials   = models.BooleanField(default=True,
                        help_text='Track individual serial numbers for this product.')

    # Image
    image           = models.ImageField(upload_to='products/', blank=True, null=True)

    # Status
    is_active       = models.BooleanField(default=True)
    created_by      = models.ForeignKey(
                        settings.AUTH_USER_MODEL,
                        on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name='products_created'
                    )
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'name']

    def __str__(self):
        parts = [self.name]
        if self.brand:
            parts.insert(0, self.brand)
        if self.model_number:
            parts.append(f'({self.model_number})')
        return ' '.join(parts)

    @property
    def current_stock(self):
        """Total sellable units in stock (excludes demo and damaged)."""
        return self.units.filter(status='in_stock', condition='new').count()

    @property
    def demo_stock(self):
        """Number of demo/floor units."""
        return self.units.filter(condition='demo').count()

    @property
    def is_low_stock(self):
        return self.current_stock <= self.reorder_point

    @property
    def profit_margin(self):
        if self.cost_price > 0:
            return round(((self.selling_price - self.cost_price) / self.cost_price) * 100, 1)
        return 0

    @property
    def warranty_display(self):
        if self.warranty_months == 0:
            return 'No warranty'
        if self.warranty_months < 12:
            return f'{self.warranty_months} month(s)'
        years = self.warranty_months // 12
        months = self.warranty_months % 12
        if months == 0:
            return f'{years} year(s)'
        return f'{years} year(s) {months} month(s)'


# ─── Product Unit (Individual Serial Number) ──────────────────────────────────

class ProductUnit(models.Model):
    STATUS_CHOICES = [
        ('in_stock',  'In Stock'),
        ('sold',      'Sold'),
        ('returned',  'Returned'),
        ('demo',      'Demo / Floor Unit'),
        ('damaged',   'Damaged'),
        ('reserved',  'Reserved'),
    ]

    CONDITION_CHOICES = [
        ('new',      'New'),
        ('refurb',   'Refurbished'),
        ('demo',     'Demo'),
        ('damaged',  'Damaged'),
    ]

    product         = models.ForeignKey(Product, on_delete=models.PROTECT,
                                        related_name='units')
    serial_number   = models.CharField(max_length=100, blank=True,
                        help_text='Leave blank if product does not use serial numbers.')
    condition       = models.CharField(max_length=20, choices=CONDITION_CHOICES, default='new')
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_stock')
    purchase_cost   = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                        help_text='Cost of this specific unit when purchased.')
    notes           = models.TextField(blank=True)

    # Tracking
    received_at     = models.DateTimeField(default=timezone.now)
    sold_at         = models.DateTimeField(null=True, blank=True)
    added_by        = models.ForeignKey(
                        settings.AUTH_USER_MODEL,
                        on_delete=models.SET_NULL,
                        null=True, blank=True,
                        related_name='units_added'
                    )

    class Meta:
        ordering = ['-received_at']
        unique_together = [['product', 'serial_number']]

    def __str__(self):
        serial = self.serial_number or 'No Serial'
        return f'{self.product.name} — {serial} [{self.get_status_display()}]'

    def mark_sold(self):
        self.status  = 'sold'
        self.sold_at = timezone.now()
        self.save(update_fields=['status', 'sold_at'])

    def mark_returned(self):
        self.status  = 'returned'
        self.sold_at = None
        self.save(update_fields=['status', 'sold_at'])

    def convert_to_demo(self):
        self.condition = 'demo'
        self.status    = 'demo'
        self.save(update_fields=['condition', 'status'])

    def convert_to_sellable(self):
        self.condition = 'new'
        self.status    = 'in_stock'
        self.save(update_fields=['condition', 'status'])