from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("", views.home, name="home"),
    path("admin-kpis/", views.admin_kpis, name="admin_kpis"),
    path("supervisor/", views.supervisor_queue, name="supervisor_queue"),
]
