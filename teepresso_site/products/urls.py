from django.urls import path

from . import views

app_name = "products"

urlpatterns = [
    path("", views.product_list, name="list"),
    path("search/", views.live_search, name="live_search"),
    path("my-designs/", views.my_designs, name="my_designs"),
    path("<slug:slug>/", views.product_detail, name="detail"),
    path("<slug:slug>/review/", views.add_review, name="add_review"),
    path("<slug:slug>/customize/", views.customize, name="customize"),
]
