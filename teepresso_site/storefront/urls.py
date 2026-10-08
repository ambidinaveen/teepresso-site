from django.urls import path

from orders import views as order_views

from . import views

app_name = "storefront"

urlpatterns = [
    path("", views.index, name="index"),
    path("track/", order_views.track, name="track"),
]
