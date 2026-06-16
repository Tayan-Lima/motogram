from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('corridas.urls')),
    path('', include('motoristas.urls')),
    path('', include('pagamentos.urls')),
    path('', include('admin_mg.urls')),
    path('', include('site_publico.urls')),
]
