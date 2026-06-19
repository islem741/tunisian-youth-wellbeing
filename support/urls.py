from django.urls import path

from . import views

app_name = "support"

urlpatterns = [
    path("mood/log/",                  views.mood_log,             name="mood_log"),
    path("mood/history/",              views.mood_history,         name="mood_history"),
    path("session/<int:youth_pk>/",    views.session_log,          name="session_log"),
    path("youth/<int:youth_pk>/",      views.youth_detail,         name="youth_detail"),
    path("escalate/<int:session_pk>/", views.escalate_session,     name="escalate_session"),
    path("resolve/<int:session_pk>/",  views.resolve_session,      name="resolve_session"),
    path("counselor/queue/",           views.counselor_queue,      name="counselor_queue"),
    path("supervisor/",                views.supervisor_dashboard, name="supervisor_dashboard"),
    path("assignments/",               views.assignment_list,      name="assignment_list"),
    path("assistant/",                 views.rag_assistant,        name="rag_assistant"),
]
