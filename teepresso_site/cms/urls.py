from django.urls import path

from . import views

app_name = "cms"

urlpatterns = [
    path("faq/", views.faq, name="faq"),
    path("contact/", views.contact, name="contact"),
    path("newsletter/subscribe/", views.newsletter_subscribe, name="newsletter"),
    path("chatbot/", views.chatbot, name="chatbot"),
    path("page/<slug:slug>/", views.page, name="page"),
]
