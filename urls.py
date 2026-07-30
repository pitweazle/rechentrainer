from django.conf import settings
from django.contrib import admin
from django.conf.urls.static import static

from django.urls import path, include
from .import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('physik/', include('physik.urls')),
    path('medien/', include('medien.urls')),
    path('', include('accounts.urls')),
    path('', include('core.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)