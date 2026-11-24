from django.urls import path

from . import aprovacao, views

app_name = "portal"

urlpatterns = [
    path("aprovacao/<str:token>/", aprovacao.pagina, name="aprovacao"),
    path("", views.chat, name="chat"),
    path("api/mensagens/", views.api_mensagens, name="api-mensagens"),
    path("api/enviar/", views.api_enviar, name="api-enviar"),
]
