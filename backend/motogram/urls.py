from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('corridas.urls')),
    path('', include('motoristas.urls')),
    path('', include('pagamentos.urls')),
    path('', include('admin_mg.urls')),
    path('', include('site_publico.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
