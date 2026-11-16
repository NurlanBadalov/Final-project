"""Project-level URL configuration."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("restaurant.urls")),
]

# During development Django serves uploaded dish images from MEDIA_ROOT.
# In production a web server (or object storage) should serve /media/ instead.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
