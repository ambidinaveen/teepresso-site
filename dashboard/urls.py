from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    # orders
    path("orders/", views.orders_list, name="orders"),
    path("orders/<str:order_no>/", views.order_detail, name="order_detail"),
    # products
    path("products/", views.products_list, name="products"),
    path("products/new/", views.product_edit, name="product_new"),
    path("products/<int:pk>/edit/", views.product_edit, name="product_edit"),
    path("products/<int:pk>/delete/", views.product_delete, name="product_delete"),
    # inventory
    path("inventory/", views.inventory, name="inventory"),
    # customers
    path("customers/", views.customers, name="customers"),
    path("customers/<int:pk>/block/", views.customer_toggle_block, name="customer_block"),
    # leads
    path("leads/", views.leads, name="leads"),
    path("leads/<int:pk>/update/", views.lead_update, name="lead_update"),
    # coupons
    path("coupons/", views.coupons, name="coupons"),
    # designs
    path("designs/", views.designs, name="designs"),
    # cms
    path("cms/<str:kind>/", views.cms_list, name="cms_list"),
    path("cms/<str:kind>/new/", views.cms_edit, name="cms_new"),
    path("cms/<str:kind>/<int:pk>/edit/", views.cms_edit, name="cms_edit"),
    path("cms/<str:kind>/<int:pk>/delete/", views.cms_delete, name="cms_delete"),
    # reports & audit
    path("reports/", views.reports, name="reports"),
    path("reports/<str:kind>.csv", views.report_export, name="report_export"),
    path("audit/", views.audit, name="audit"),
]
