from django.urls import path

from . import views

app_name = "portal"

urlpatterns = [
    path("", views.chat, name="chat"),
    path("api/mensagens/", views.api_mensagens, name="api-mensagens"),
    path("api/enviar/", views.api_enviar, name="api-enviar"),
]
