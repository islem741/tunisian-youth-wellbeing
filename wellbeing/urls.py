"""Root URL configuration for the Youth Mental Health Peer-Support Platform."""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from gql.schema import graphql_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/",  include("accounts.urls",  namespace="accounts")),
    path("cases/",     include("cases.urls",     namespace="cases")),
    path("support/",   include("support.urls",   namespace="support")),
    path("dashboard/", include("dashboard.urls", namespace="dashboard")),
    path("api/",       include("cases.api.urls")),
    # GraphQL endpoint — GraphiQL playground available at /graphql/ in DEBUG mode
    path("graphql/",   graphql_view, name="graphql"),
    path("", RedirectView.as_view(pattern_name="dashboard:home", permanent=False)),
]
