from django.urls import path

from . import views

app_name = "cases"

urlpatterns = [
    path("", views.case_list, name="list"),
    path("new/", views.assessment_create, name="assessment_create"),
    path("upload/", views.assessment_upload_csv, name="assessment_upload"),
    path("student/new/", views.student_create, name="student_create"),
    path("<int:pk>/", views.case_detail, name="detail"),
    path("<int:pk>/transition/", views.case_transition, name="transition"),
    path("<int:pk>/appointment/new/", views.appointment_create, name="appointment_create"),
    path("appointment/<int:pk>/miss/", views.appointment_mark_missed, name="appointment_miss"),
    path("policy/", views.risk_policy_edit, name="risk_policy"),
    path("export.csv", views.export_cases_csv, name="export_csv"),
]
