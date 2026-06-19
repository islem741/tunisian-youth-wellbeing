from django.contrib import admin

from .models import CaseEvent, InterventionPlan, SERSEntry, SERSPolicy, Student


@admin.register(SERSPolicy)
class SERSPolicyAdmin(admin.ModelAdmin):
    list_display = ("high_threshold", "medium_threshold", "updated_at", "updated_by")
    readonly_fields = ("updated_at",)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("external_id", "last_name", "first_name", "school", "region", "age")
    list_filter = ("school", "region", "gender")
    search_fields = ("external_id", "first_name", "last_name")


@admin.register(SERSEntry)
class SERSEntryAdmin(admin.ModelAdmin):
    list_display = (
        "student", "sers_score", "risk_level", "workflow_state",
        "operator", "period_label", "created_at",
    )
    list_filter = ("risk_level", "workflow_state", "student__school")
    readonly_fields = ("sers_score", "risk_level", "risk_explanation", "created_at", "updated_at")
    search_fields = ("student__external_id", "student__last_name")


@admin.register(InterventionPlan)
class InterventionPlanAdmin(admin.ModelAdmin):
    list_display = ("entry", "plan_type", "assigned_to", "due_date", "status")
    list_filter = ("status", "plan_type")


@admin.register(CaseEvent)
class CaseEventAdmin(admin.ModelAdmin):
    list_display = ("entry", "action", "actor", "from_state", "to_state", "created_at")
    list_filter = ("action",)
    readonly_fields = ("created_at",)
