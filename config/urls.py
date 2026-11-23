from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Central de TI - Administração"
admin.site.site_title = "Central de TI"
admin.site.index_title = "Base de conhecimento, conversas e chamados"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("painel/", include("apps.painel.urls")),
    path("webhooks/digisac/", include("apps.digisac.urls")),
    path("", include("apps.portal.urls")),
]
