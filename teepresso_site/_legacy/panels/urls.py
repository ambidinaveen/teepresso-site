from django.urls import path

from . import views

app_name = "panels"

urlpatterns = [
    path("", views.home_redirect, name="home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    # Admin
    path("admin/", views.admin_dashboard, name="admin_dashboard"),
    path("orders/", views.order_management, name="order_management"),
    path("orders/api/", views.orders_api, name="orders_api"),
    path("orders/<str:order_no>/status/", views.update_status, name="update_status"),
    path("orders/<str:order_no>/send-bill/", views.send_bill_action, name="send_bill"),
    path("orders/<str:order_no>/", views.order_detail, name="order_detail"),

    # Manager
    path("manager/", views.manager_inventory, name="manager_inventory"),
    path("manager/stock/", views.stock_action, name="stock_action"),
    path("manager/offline/", views.offline_order, name="offline_order"),

    # Editor
    path("editor/", views.editor_mockups, name="editor_mockups"),
    path("editor/<str:order_no>/approve/", views.mockup_approve, name="mockup_approve"),

    # Dispatch
    path("dispatch/", views.dispatch, name="dispatch"),
    path("dispatch/<str:order_no>/process/", views.dispatch_process, name="dispatch_process"),
]
