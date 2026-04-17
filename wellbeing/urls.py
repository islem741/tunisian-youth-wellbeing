"""Root URL configuration for the Tunisian Youth Well-being platform."""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls", namespace="accounts")),
    path("cases/", include("cases.urls", namespace="cases")),
    path("dashboard/", include("dashboard.urls", namespace="dashboard")),
    path("", RedirectView.as_view(pattern_name="dashboard:home", permanent=False)),
]
