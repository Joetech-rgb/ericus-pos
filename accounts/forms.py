from django import forms
from django.contrib.auth.password_validation import validate_password
from .models import User


# ─── Login ────────────────────────────────────────────────────────────────────

class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class':       'form-control',
            'placeholder': 'Username',
            'autofocus':   True,
        }),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class':       'form-control',
            'placeholder': 'Password',
        }),
    )


# ─── Register Shop ────────────────────────────────────────────────────────────

class RegisterShopForm(forms.Form):
    # Owner account
    full_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your full name'}),
    )
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'}),
    )
    pin = forms.CharField(
        max_length=6,
        required=False,
        initial='0000',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Owner PIN (default: 0000)'}),
    )

    # Shop profile
    shop_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Shop name'}),
    )
    address = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Shop address'}),
    )
    shop_phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Shop phone'}),
    )
    whatsapp = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'WhatsApp number'}),
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Shop email'}),
    )
    logo = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'}),
    )

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def clean_pin(self):
        pin = self.cleaned_data.get('pin') or '0000'
        if not pin.isdigit():
            raise forms.ValidationError('PIN must contain digits only.')
        if len(pin) < 4 or len(pin) > 6:
            raise forms.ValidationError('PIN must be 4–6 digits.')
        return pin

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password')
        p2 = cleaned.get('confirm_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', 'Passwords do not match.')
        return cleaned


# ─── Create User ──────────────────────────────────────────────────────────────

class CreateUserForm(forms.Form):
    full_name = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name'}),
    )
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'}),
    )
    role = forms.ChoiceField(
        choices=[('attendant', 'Attendant')],
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'}),
    )

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('This username is already taken.')
        return username

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('password')
        p2 = cleaned.get('confirm_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', 'Passwords do not match.')
        return cleaned


# ─── Edit User ────────────────────────────────────────────────────────────────

class EditUserForm(forms.ModelForm):
    class Meta:
        model  = User
        fields = ['full_name', 'phone', 'role']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone':     forms.TextInput(attrs={'class': 'form-control'}),
            'role':      forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Attendants cannot be promoted to owner via this form
        self.fields['role'].choices = [
            c for c in self.fields['role'].choices
            if c[0] != 'owner'
        ]


# ─── Change PIN ───────────────────────────────────────────────────────────────

class ChangePINForm(forms.Form):
    old_pin = forms.CharField(
        max_length=6,
        widget=forms.PasswordInput(attrs={
            'class':       'form-control',
            'placeholder': 'Current PIN',
            'inputmode':   'numeric',
            'maxlength':   '6',
        }),
    )
    new_pin = forms.CharField(
        max_length=6,
        widget=forms.PasswordInput(attrs={
            'class':       'form-control',
            'placeholder': 'New PIN (4–6 digits)',
            'inputmode':   'numeric',
            'maxlength':   '6',
        }),
    )
    confirm_pin = forms.CharField(
        max_length=6,
        widget=forms.PasswordInput(attrs={
            'class':       'form-control',
            'placeholder': 'Confirm new PIN',
            'inputmode':   'numeric',
            'maxlength':   '6',
        }),
    )

    def clean_new_pin(self):
        pin = self.cleaned_data.get('new_pin', '')
        if not pin.isdigit():
            raise forms.ValidationError('PIN must contain digits only.')
        if len(pin) < 4:
            raise forms.ValidationError('PIN must be at least 4 digits.')
        return pin

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('new_pin')
        p2 = cleaned.get('confirm_pin')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_pin', 'PINs do not match.')
        return cleaned


# ─── Change Password ──────────────────────────────────────────────────────────

class ChangePasswordForm(forms.Form):
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class':       'form-control',
            'placeholder': 'Current password',
        }),
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class':       'form-control',
            'placeholder': 'New password',
        }),
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class':       'form-control',
            'placeholder': 'Confirm new password',
        }),
    )

    def clean_new_password(self):
        password = self.cleaned_data.get('new_password')
        if password:
            validate_password(password)
        return password

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get('new_password')
        p2 = cleaned.get('confirm_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', 'Passwords do not match.')
        return cleaned