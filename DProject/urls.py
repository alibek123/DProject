from django.contrib import admin
from django.urls import path, include
from api_basic.views import UserCreate
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
                  path('admin/', admin.site.urls),
                  path('api/', include('api_basic.urls')),
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
