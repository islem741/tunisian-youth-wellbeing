from django.contrib import admin

from .models import Assignment, AuditEvent, MoodScore, SupportSession


@admin.register(MoodScore)
class MoodScoreAdmin(admin.ModelAdmin):
    list_display = ("youth", "score", "created_at")
    list_filter = ("score",)
    search_fields = ("youth__username", "youth__first_name", "youth__last_name")


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("youth", "peer_supporter", "counselor", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = (
        "youth__username",
        "peer_supporter__username",
        "counselor__username",
    )


@admin.register(SupportSession)
class SupportSessionAdmin(admin.ModelAdmin):
    list_display = (
        "assignment",
        "logged_by",
        "session_date",
        "escalation_status",
        "created_at",
    )
    list_filter = ("escalation_status", "session_date")
    readonly_fields = ("escalated_at", "escalated_by", "created_at", "updated_at")


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ("action", "actor", "youth", "created_at")
    list_filter = ("action",)
    readonly_fields = ("created_at",)
