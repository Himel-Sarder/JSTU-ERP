"""URL map for the JSTU ERP."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("gate/", include("accounts.urls")),
    path("student/", include("studentpanel.urls")),
    path("teacher/", include("teacherpanel.urls")),
    path("registrar/", include("adminpanel.urls")),
    path("portal/", include("portal.urls")),
    path("", RedirectView.as_view(pattern_name="accounts:gate", permanent=False)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
