from django.urls import path

from .views import receber_webhook

urlpatterns = [
    path("", receber_webhook, name="digisac-webhook"),
]
