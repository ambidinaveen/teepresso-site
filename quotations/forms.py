from django import forms

from .models import CorporateLead

_INPUT = {"class": "form-control"}


class QuotationForm(forms.ModelForm):
    class Meta:
        model = CorporateLead
        fields = ("company_name", "contact_person", "email", "phone",
                  "product_requirement", "quantity", "budget", "reference_file")
        widgets = {
            "company_name": forms.TextInput(attrs=_INPUT),
            "contact_person": forms.TextInput(attrs=_INPUT),
            "email": forms.EmailInput(attrs=_INPUT),
            "phone": forms.TextInput(attrs=_INPUT),
            "product_requirement": forms.Textarea(attrs={**_INPUT, "rows": 3}),
            "quantity": forms.NumberInput(attrs=_INPUT),
            "budget": forms.TextInput(attrs={**_INPUT, "placeholder": "e.g. ₹50,000"}),
            "reference_file": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }
