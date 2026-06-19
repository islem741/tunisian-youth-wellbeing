from django.urls import path

from . import views

app_name = "cases"

urlpatterns = [
    path("",                             views.case_list,            name="list"),
    path("entry/new/",                   views.entry_create,         name="entry_create"),
    path("entry/upload/",                views.entry_upload_csv,     name="entry_upload"),
    path("student/new/",                 views.student_create,       name="student_create"),
    path("<int:pk>/",                    views.case_detail,          name="detail"),
    path("<int:pk>/transition/",         views.case_transition,      name="transition"),
    path("<int:entry_pk>/intervention/", views.intervention_create,  name="intervention_create"),
    path("intervention/<int:plan_pk>/complete/",
         views.intervention_complete,                                name="intervention_complete"),
    path("policy/",                      views.sers_policy_edit,     name="sers_policy"),
    path("export.csv",                   views.export_cases_csv,     name="export_csv"),
]
