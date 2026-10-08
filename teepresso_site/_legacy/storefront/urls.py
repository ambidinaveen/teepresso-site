from django.urls import path

from . import views

app_name = "storefront"

urlpatterns = [
    path("", views.index, name="index"),
    path("design/<int:product_id>/", views.configurator, name="configurator"),
    path("api/price/", views.price_api, name="price_api"),
    path("register/", views.register, name="register"),
    path("checkout/", views.checkout, name="checkout"),
    path("place-order/", views.place_order, name="place_order"),
    path("order/<str:order_no>/", views.confirmation, name="confirmation"),
    path("bill/<str:order_no>/", views.bill, name="bill"),
    path("track/", views.tracking, name="tracking"),
    path("track/<str:order_no>/", views.tracking, name="tracking_detail"),
]
