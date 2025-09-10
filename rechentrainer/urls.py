from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # Apps
    path('', include('accounts.urls')),
    path('', include('duell.urls')),
    path('', include('medien.urls')),
    #path('onlineduell/', include('onlineduell.urls')),  # falls diese App eigene URLs bekommt
    path('', include('core.urls')),  # Catch-All / Home-Funktion am Ende

] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
