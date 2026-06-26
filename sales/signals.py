"""
sales/signals.py

Post-sale signals. Connect these in sales/apps.py ready() method.
Currently the main checkout logic in utils.py handles stock and payments
directly inside the transaction — signals are used for non-critical
side effects that run after the commit.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver


# Import lazily inside handlers to avoid circular imports
@receiver(post_save, sender='sales.Sale')
def on_sale_created(sender, instance, created, **kwargs):
    """After a sale is saved, run non-critical side effects."""
    if not created:
        return  # Sales are locked; only care about creation

    # Update customer last_purchase_date if linked
    if instance.customer_id:
        try:
            from customers.models import Customer
            from django.utils import timezone
            Customer.objects.filter(pk=instance.customer_id).update(
                last_purchase_date=instance.created_at.date()
            )
        except Exception:
            pass