from django import forms

from blogs.models import Blog
from cart.models import Coupon
from cms.models import Banner, FAQ, Testimonial
from products.models import Product

_C = {"class": "form-control"}
_S = {"class": "form-select"}
_CK = {"class": "form-check-input"}


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ("name", "category", "brand", "sku", "short_description", "description",
                  "specifications", "image", "base_price", "sale_price", "min_order_qty",
                  "is_customizable", "featured", "trending", "best_seller", "active")
        widgets = {
            "name": forms.TextInput(attrs=_C),
            "category": forms.Select(attrs=_S),
            "brand": forms.Select(attrs=_S),
            "sku": forms.TextInput(attrs=_C),
            "short_description": forms.TextInput(attrs=_C),
            "description": forms.Textarea(attrs={**_C, "rows": 4}),
            "specifications": forms.Textarea(attrs={**_C, "rows": 4}),
            "image": forms.ClearableFileInput(attrs=_C),
            "base_price": forms.NumberInput(attrs=_C),
            "sale_price": forms.NumberInput(attrs=_C),
            "min_order_qty": forms.NumberInput(attrs=_C),
            "is_customizable": forms.CheckboxInput(attrs=_CK),
            "featured": forms.CheckboxInput(attrs=_CK),
            "trending": forms.CheckboxInput(attrs=_CK),
            "best_seller": forms.CheckboxInput(attrs=_CK),
            "active": forms.CheckboxInput(attrs=_CK),
        }


class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = ("code", "kind", "value", "min_order", "description", "active", "expires")
        widgets = {
            "code": forms.TextInput(attrs=_C),
            "kind": forms.Select(attrs=_S),
            "value": forms.NumberInput(attrs=_C),
            "min_order": forms.NumberInput(attrs=_C),
            "description": forms.TextInput(attrs=_C),
            "active": forms.CheckboxInput(attrs=_CK),
            "expires": forms.DateInput(attrs={**_C, "type": "date"}),
        }


class BannerForm(forms.ModelForm):
    class Meta:
        model = Banner
        fields = ("title", "subtitle", "image", "cta_text", "cta_link",
                  "bg_gradient", "sort", "active")
        widgets = {f: forms.TextInput(attrs=_C)
                   for f in ("title", "subtitle", "cta_text", "cta_link", "bg_gradient")}


class FAQForm(forms.ModelForm):
    class Meta:
        model = FAQ
        fields = ("question", "answer", "category", "sort", "active")
        widgets = {
            "question": forms.TextInput(attrs=_C),
            "answer": forms.Textarea(attrs={**_C, "rows": 3}),
            "category": forms.TextInput(attrs=_C),
        }


class BlogForm(forms.ModelForm):
    class Meta:
        model = Blog
        fields = ("title", "category", "author", "cover", "excerpt", "body", "published")
        widgets = {
            "title": forms.TextInput(attrs=_C),
            "category": forms.Select(attrs=_S),
            "author": forms.TextInput(attrs=_C),
            "excerpt": forms.TextInput(attrs=_C),
            "body": forms.Textarea(attrs={**_C, "rows": 8}),
        }


class TestimonialForm(forms.ModelForm):
    class Meta:
        model = Testimonial
        fields = ("name", "role", "avatar", "rating", "quote", "is_corporate", "active")
        widgets = {
            "name": forms.TextInput(attrs=_C),
            "role": forms.TextInput(attrs=_C),
            "rating": forms.NumberInput(attrs=_C),
            "quote": forms.Textarea(attrs={**_C, "rows": 3}),
        }
