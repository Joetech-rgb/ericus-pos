from django.db import models
from django.conf import settings
from django.utils import timezone


class ExpenseCategory(models.Model):
    """
    Groups expenses into types — Rent, Utilities, Salaries, Transport, etc.
    Owner can create custom categories.
    """
    name        = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon        = models.CharField(max_length=50, default='fa-receipt',
                                   help_text='Font Awesome icon class e.g. fa-bolt')
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Expense Category'
        verbose_name_plural = 'Expense Categories'

    def __str__(self):
        return self.name


class Expense(models.Model):
    """
    A single shop expense — anything money goes out on besides purchasing stock.
    e.g. rent, electricity, salaries, delivery, repairs, stationery.
    """

    # ── Payment methods ───────────────────────────────────────────────────────
    PAYMENT_CASH  = 'cash'
    PAYMENT_MOMO  = 'momo'
    PAYMENT_BANK  = 'bank'
    PAYMENT_CHOICES = [
        (PAYMENT_CASH, 'Cash'),
        (PAYMENT_MOMO, 'Mobile Money (MoMo)'),
        (PAYMENT_BANK, 'Bank Transfer'),
    ]

    # ── Status ────────────────────────────────────────────────────────────────
    STATUS_PENDING  = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_CHOICES  = [
        (STATUS_PENDING,  'Pending Approval'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    # ── Core fields ───────────────────────────────────────────────────────────
    category       = models.ForeignKey(
        ExpenseCategory, on_delete=models.PROTECT,
        related_name='expenses'
    )
    title          = models.CharField(max_length=200,
                                      help_text='Short description e.g. "Monthly rent — May 2026"')
    amount         = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=10, choices=PAYMENT_CHOICES,
                                      default=PAYMENT_CASH)
    reference      = models.CharField(max_length=100, blank=True,
                                      help_text='MoMo transaction ID, cheque number, or bank ref')
    expense_date   = models.DateField(default=timezone.now,
                                      help_text='Date the expense was incurred')
    notes          = models.TextField(blank=True)
    receipt_image  = models.ImageField(
        upload_to='expenses/receipts/%Y/%m/',
        blank=True, null=True,
        help_text='Photo of physical receipt (optional)'
    )

    # ── Approval workflow ─────────────────────────────────────────────────────
    status       = models.CharField(max_length=10, choices=STATUS_CHOICES,
                                    default=STATUS_PENDING, db_index=True)
    approved_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='expenses_approved'
    )
    approved_at  = models.DateTimeField(null=True, blank=True)
    reject_reason = models.TextField(blank=True)

    # ── Recurring flag ────────────────────────────────────────────────────────
    is_recurring     = models.BooleanField(
        default=False,
        help_text='Tick if this expense repeats regularly (e.g. monthly rent).'
    )
    recurrence_note  = models.CharField(
        max_length=100, blank=True,
        help_text='e.g. "Every 1st of the month"'
    )

    # ── Meta ──────────────────────────────────────────────────────────────────
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='expenses_recorded'
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-expense_date', '-created_at']
        verbose_name = 'Expense'
        verbose_name_plural = 'Expenses'
        indexes = [
            models.Index(fields=['expense_date']),
            models.Index(fields=['status', 'expense_date']),
            models.Index(fields=['category', 'expense_date']),
        ]

    def __str__(self):
        return f'{self.title} — GH₵{self.amount} ({self.expense_date})'

    # ── Status helpers ────────────────────────────────────────────────────────

    @property
    def is_pending(self):
        return self.status == self.STATUS_PENDING

    @property
    def is_approved(self):
        return self.status == self.STATUS_APPROVED

    @property
    def is_rejected(self):
        return self.status == self.STATUS_REJECTED

    def approve(self, owner):
        self.status      = self.STATUS_APPROVED
        self.approved_by = owner
        self.approved_at = timezone.now()
        self.reject_reason = ''
        self.save(update_fields=['status', 'approved_by', 'approved_at', 'reject_reason', 'updated_at'])

    def reject(self, owner, reason=''):
        self.status        = self.STATUS_REJECTED
        self.approved_by   = owner
        self.approved_at   = timezone.now()
        self.reject_reason = reason
        self.save(update_fields=['status', 'approved_by', 'approved_at', 'reject_reason', 'updated_at'])