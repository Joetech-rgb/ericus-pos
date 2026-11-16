from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.conf import settings


# ─── User Manager ─────────────────────────────────────────────────────────────

class UserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('Username is required')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('role', 'owner')
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, password, **extra_fields)


# ─── User ─────────────────────────────────────────────────────────────────────

class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('attendant', 'Attendant'),
    ]

    username        = models.CharField(max_length=50, unique=True)
    full_name       = models.CharField(max_length=100)
    role            = models.CharField(max_length=20, choices=ROLE_CHOICES, default='attendant')
    phone           = models.CharField(max_length=20, blank=True)
    is_active       = models.BooleanField(default=True)
    is_staff        = models.BooleanField(default=False)
    dark_mode       = models.BooleanField(default=False)
    date_joined     = models.DateTimeField(default=timezone.now)

    objects = UserManager()

    USERNAME_FIELD  = 'username'
    REQUIRED_FIELDS = ['full_name']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def __str__(self):
        return f"{self.full_name} ({self.get_role_display()})"

    @property
    def is_owner(self):
        return self.role == 'owner'

    @property
    def is_attendant(self):
        return self.role == 'attendant'


# ─── Shop Profile ─────────────────────────────────────────────────────────────

class ShopProfile(models.Model):
    owner           = models.OneToOneField(User, on_delete=models.CASCADE, related_name='shop')
    name            = models.CharField(max_length=100, default='Adjei’s God First Ventures')
    tagline         = models.CharField(max_length=200, blank=True, default='Quality Products, Trusted Service')
    logo            = models.ImageField(upload_to='shop/', blank=True, null=True)
    address         = models.TextField(blank=True)
    phone           = models.CharField(max_length=20, blank=True)
    whatsapp        = models.CharField(max_length=20, blank=True)
    email           = models.EmailField(blank=True)
    receipt_footer  = models.CharField(
        max_length=200,
        blank=True,
        default='Thank you for shopping at Adjei’s God First Ventures! All sales are final unless faulty.'
    )
    currency_symbol = models.CharField(max_length=5, default='GH₵')
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Shop Profile'

    def __str__(self):
        return self.name


# ─── Owner PIN ────────────────────────────────────────────────────────────────

class OwnerPIN(models.Model):
    user            = models.OneToOneField(User, on_delete=models.CASCADE, related_name='pin')
    pin_hash        = models.CharField(max_length=128)   # Stored as hashed value
    attempts        = models.PositiveIntegerField(default=0)
    locked_until    = models.DateTimeField(null=True, blank=True)
    last_used       = models.DateTimeField(null=True, blank=True)
    created_at      = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Owner PIN'

    def __str__(self):
        return f"PIN for {self.user.full_name}"

    @property
    def is_locked(self):
        if self.locked_until and timezone.now() < self.locked_until:
            return True
        return False

    def increment_attempts(self):
        self.attempts += 1
        max_attempts = getattr(settings, 'PIN_MAX_ATTEMPTS', 3)
        lockout_minutes = getattr(settings, 'PIN_LOCKOUT_MINUTES', 30)
        if self.attempts >= max_attempts:
            self.locked_until = timezone.now() + timedelta(minutes=lockout_minutes)
        self.save()

    def reset_attempts(self):
        self.attempts = 0
        self.locked_until = None
        self.last_used = timezone.now()
        self.save()


# ─── Failed PIN Log ───────────────────────────────────────────────────────────

class FailedPINAttempt(models.Model):
    user            = models.ForeignKey(User, on_delete=models.CASCADE, related_name='failed_pins')
    action_attempted = models.CharField(max_length=100)   # e.g. "discount", "return", "stock_adjust"
    timestamp       = models.DateTimeField(auto_now_add=True)
    ip_address      = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = 'Failed PIN Attempt'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user.full_name} failed PIN at {self.timestamp:%Y-%m-%d %H:%M}"


# ─── User Session (Online Tracker) ───────────────────────────────────────────

class UserSession(models.Model):
    user            = models.OneToOneField(User, on_delete=models.CASCADE, related_name='session_tracker')
    session_key     = models.CharField(max_length=40, blank=True)
    last_activity   = models.DateTimeField(default=timezone.now)
    ip_address      = models.GenericIPAddressField(null=True, blank=True)
    device          = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = 'User Session'

    def __str__(self):
        return f"{self.user.full_name} — last active {self.last_activity:%H:%M}"

    @property
    def is_online(self):
        timeout = getattr(settings, 'USER_ONLINE_TIMEOUT', 5)
        cutoff = timezone.now() - timedelta(minutes=timeout)
        return self.last_activity >= cutoff

    def update_activity(self, session_key=None, ip=None, device=None):
        self.last_activity = timezone.now()
        if session_key:
            self.session_key = session_key
        if ip:
            self.ip_address = ip
        if device:
            self.device = device
        self.save(update_fields=['last_activity', 'session_key', 'ip_address', 'device'])