from django.urls import path

from .views import CaseEventListView, SERSEntryDetailView, SERSEntryListView

urlpatterns = [
    path("cases/",          SERSEntryListView.as_view(),   name="api-cases-list"),
    path("cases/<int:pk>/", SERSEntryDetailView.as_view(), name="api-cases-detail"),
    path("cases/<int:pk>/events/", CaseEventListView.as_view(), name="api-cases-events"),
]
