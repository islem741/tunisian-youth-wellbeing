from django.contrib import admin

from .models import Appointment, CaseEvent, RiskPolicy, Student, StressAssessment


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("external_id", "first_name", "last_name", "school", "region", "age")
    list_filter = ("school", "region", "gender")
    search_fields = ("external_id", "first_name", "last_name")


@admin.register(StressAssessment)
class StressAssessmentAdmin(admin.ModelAdmin):
    list_display = ("student", "total_score", "risk_level", "workflow_state", "operator", "created_at")
    list_filter = ("risk_level", "workflow_state")
    readonly_fields = ("total_score", "risk_level", "risk_explanation", "created_at", "updated_at")


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("assessment", "scheduled_for", "status", "scheduled_by")
    list_filter = ("status",)


@admin.register(CaseEvent)
class CaseEventAdmin(admin.ModelAdmin):
    list_display = ("assessment", "action", "actor", "created_at")
    list_filter = ("action",)


@admin.register(RiskPolicy)
class RiskPolicyAdmin(admin.ModelAdmin):
    list_display = ("threshold", "updated_at", "updated_by")
