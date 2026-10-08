from django.urls import path

from . import views

app_name = "cart"

urlpatterns = [
    path("", views.detail, name="detail"),
    path("add/<int:product_id>/", views.add, name="add"),
    path("update/<int:item_id>/", views.update, name="update"),
    path("remove/<int:item_id>/", views.remove, name="remove"),
    path("save/<int:item_id>/", views.save_for_later, name="save_for_later"),
    path("coupon/apply/", views.apply_coupon, name="apply_coupon"),
    path("coupon/remove/", views.remove_coupon, name="remove_coupon"),
]
