from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "painel"

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="painel/login.html",
                                                redirect_authenticated_user=True), name="login"),
    path("sair/", auth_views.LogoutView.as_view(), name="sair"),
    path("", views.fila, name="fila"),
    path("exportar.xlsx", views.exportar, name="exportar"),
    path("chamado/<str:protocolo>/", views.detalhe, name="detalhe"),
    path("chamado/<str:protocolo>/acao/", views.acao, name="acao"),
    path("chamado/<str:protocolo>/mensagens/", views.mensagens, name="mensagens"),
]
