from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("forgot/", views.forgot_password, name="forgot"),
    path("", views.dashboard, name="dashboard"),
    path("profile/", views.profile, name="profile"),
    path("orders/", views.order_list, name="orders"),
    path("orders/<str:order_no>/", views.order_detail, name="order_detail"),
    path("addresses/", views.addresses, name="addresses"),
    path("addresses/<int:pk>/delete/", views.address_delete, name="address_delete"),
    path("wishlist/", views.wishlist, name="wishlist"),
    path("wishlist/<int:product_id>/toggle/", views.wishlist_toggle, name="wishlist_toggle"),
]
