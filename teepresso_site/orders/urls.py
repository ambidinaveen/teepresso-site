from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("checkout/", views.checkout, name="checkout"),
    path("confirmation/<str:order_no>/", views.confirmation, name="confirmation"),
    path("invoice/<str:order_no>/", views.invoice, name="invoice"),
    path("track/", views.track, name="track"),
    path("track/<str:order_no>/", views.track, name="track_order"),
]
