from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("pay/<str:order_no>/", views.pay, name="pay"),
    path("upi/<str:order_no>/confirm/", views.upi_confirm, name="upi_confirm"),
    path("simulate/<str:order_no>/", views.simulate_success, name="simulate_success"),
    path("enquiry/<str:order_no>/", views.place_as_enquiry, name="place_as_enquiry"),
    path("callback/", views.callback, name="callback"),
]
