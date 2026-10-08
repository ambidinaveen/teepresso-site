from django import forms
from django.contrib.auth import get_user_model

from .models import Address

User = get_user_model()

_INPUT = {"class": "form-control"}


class RegisterForm(forms.ModelForm):
    full_name = forms.CharField(max_length=120, widget=forms.TextInput(attrs=_INPUT))
    password = forms.CharField(widget=forms.PasswordInput(attrs=_INPUT), min_length=6)
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs=_INPUT))

    class Meta:
        model = User
        fields = ("full_name", "email", "phone", "password", "confirm_password")
        widgets = {
            "email": forms.EmailInput(attrs=_INPUT),
            "phone": forms.TextInput(attrs=_INPUT),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_phone(self):
        phone = "".join(c for c in (self.cleaned_data.get("phone") or "") if c.isdigit())
        if len(phone) < 10:
            raise forms.ValidationError("Enter a valid 10-digit mobile number.")
        return phone

    def clean(self):
        data = super().clean()
        if data.get("password") != data.get("confirm_password"):
            self.add_error("confirm_password", "Passwords do not match.")
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        name = self.cleaned_data["full_name"].strip()
        first, _, last = name.partition(" ")
        user.first_name, user.last_name = first, last
        user.username = self.cleaned_data["email"]
        user.role = User.Role.CUSTOMER
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class LoginForm(forms.Form):
    identifier = forms.CharField(
        label="Email or Mobile", widget=forms.TextInput(attrs={**_INPUT, "autofocus": True})
    )
    password = forms.CharField(widget=forms.PasswordInput(attrs=_INPUT))


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "phone", "company", "gst_number")
        widgets = {f: forms.TextInput(attrs=_INPUT)
                   for f in ("first_name", "last_name", "phone", "company", "gst_number")}


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ("label", "full_name", "phone", "line1", "line2",
                  "city", "state", "pincode", "is_default")
        widgets = {
            **{f: forms.TextInput(attrs=_INPUT)
               for f in ("label", "full_name", "phone", "line1", "line2",
                         "city", "state", "pincode")},
            "is_default": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }
