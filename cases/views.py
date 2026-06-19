from __future__ import annotations

import csv
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import Role
from accounts.permissions import role_required

from .forms import (
    CaseTransitionForm, InterventionPlanForm,
    SERSCSVUploadForm, SERSEntryForm, SERSPolicyForm, StudentForm,
)
from .models import (
    ALLOWED_TRANSITIONS, CaseEvent, InterventionPlan,
    RiskLevel, SERSEntry, SERSPolicy, Student, WorkflowState,
)
from .services import ingest_sers_csv

logger = logging.getLogger("wellbeing.cases")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scoped_entries(user):
    """Return a QuerySet scoped to what this user may see."""
    qs = SERSEntry.objects.select_related("student", "operator")
    if user.is_program_admin or user.is_supervisor:
        return qs
    if user.is_operator:
        base = qs.filter(operator=user)
        if user.school:
            base = (base | qs.filter(student__school=user.school)).distinct()
        return base
    return qs.none()


# ---------------------------------------------------------------------------
# Case list & detail
# ---------------------------------------------------------------------------

@login_required
def case_list(request):
    qs = _scoped_entries(request.user).order_by("-created_at")
    state    = request.GET.get("state", "")
    risk     = request.GET.get("risk", "")
    school_q = request.GET.get("school", "")
    region_q = request.GET.get("region", "")
    if state:    qs = qs.filter(workflow_state=state)
    if risk:     qs = qs.filter(risk_level=risk)
    if school_q: qs = qs.filter(student__school__icontains=school_q)
    if region_q: qs = qs.filter(student__region__icontains=region_q)
    return render(request, "cases/case_list.html", {
        "entries":         qs,
        "state_choices":   WorkflowState.choices,
        "risk_choices":    RiskLevel.choices,
        "selected_state":  state,
        "selected_risk":   risk,
        "selected_school": school_q,
        "selected_region": region_q,
    })


@login_required
def case_detail(request, pk):
    # Fetch the entry without scoping first so we can log security events
    # for out-of-scope access attempts before raising 403.
    from django.shortcuts import get_object_or_404
    full_qs = SERSEntry.objects.select_related("student", "operator")
    entry = get_object_or_404(full_qs, pk=pk)

    # Operators may only see entries for their own submissions or their school.
    if request.user.is_operator:
        in_scope = (
            entry.operator == request.user
            or entry.student.school == request.user.school
        )
        if not in_scope:
            CaseEvent.objects.create(
                entry=entry, actor=request.user,
                action=CaseEvent.Action.SECURITY,
                detail=(
                    f"Operator {request.user.username} attempted to view "
                    f"entry #{pk} outside their scope."
                ),
            )
            raise PermissionDenied("You may not access this case.")
    current  = WorkflowState(entry.workflow_state)
    allowed  = [
        (v, l) for v, l in WorkflowState.choices
        if v in ALLOWED_TRANSITIONS[current.value]
    ]
    events   = entry.events.select_related("actor").order_by("-created_at")
    plans    = entry.interventions.select_related("assigned_to").order_by("due_date")
    transition_form   = CaseTransitionForm(allowed_states=allowed)
    intervention_form = InterventionPlanForm()
    return render(request, "cases/case_detail.html", {
        "entry":              entry,
        "events":             events,
        "plans":              plans,
        "transition_form":    transition_form,
        "intervention_form":  intervention_form,
        "allowed_transitions": allowed,
    })


# ---------------------------------------------------------------------------
# Student
# ---------------------------------------------------------------------------

@role_required(Role.OPERATOR, Role.ADMIN)
def student_create(request):
    form = StudentForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Student record created.")
        return redirect("cases:list")
    return render(request, "cases/student_form.html", {"form": form})


# ---------------------------------------------------------------------------
# SERS Entry (single form)
# ---------------------------------------------------------------------------

@role_required(Role.OPERATOR, Role.ADMIN)
def entry_create(request):
    form = SERSEntryForm(request.POST or None)
    if form.is_valid():
        entry = form.save(commit=False)
        entry.operator = request.user
        entry.save()
        CaseEvent.objects.create(
            entry=entry, actor=request.user,
            action=CaseEvent.Action.INTAKE,
            to_state=entry.workflow_state,
            detail=(
                f"Manual entry. SERS={entry.sers_score} "
                f"({entry.get_risk_level_display()}). "
                f"{entry.risk_explanation}"
            ),
        )
        messages.success(
            request,
            f"Entry created. SERS score: {entry.sers_score} "
            f"({entry.get_risk_level_display()}). {entry.risk_explanation}",
        )
        return redirect("cases:detail", pk=entry.pk)
    return render(request, "cases/entry_form.html", {"form": form})


# ---------------------------------------------------------------------------
# CSV bulk upload
# ---------------------------------------------------------------------------

@role_required(Role.OPERATOR, Role.ADMIN)
def entry_upload_csv(request):
    form   = SERSCSVUploadForm(request.POST or None, request.FILES or None)
    result = None
    if request.method == "POST" and form.is_valid():
        result = ingest_sers_csv(
            request.FILES["csv_file"],
            operator=request.user,
            period_label=form.cleaned_data.get("period_label", ""),
        )
        if result.created:
            messages.success(request, f"{result.created} entries imported successfully.")
        if result.errors:
            messages.warning(
                request,
                f"{result.skipped} row(s) rejected. See details below.",
            )
    return render(request, "cases/entry_upload.html", {"form": form, "result": result})


# ---------------------------------------------------------------------------
# Workflow transition
# ---------------------------------------------------------------------------

@role_required(Role.SUPERVISOR, Role.ADMIN)
def case_transition(request, pk):
    entry   = get_object_or_404(SERSEntry, pk=pk)
    current = WorkflowState(entry.workflow_state)
    allowed = [
        (v, l) for v, l in WorkflowState.choices
        if v in ALLOWED_TRANSITIONS[current.value]
    ]
    form = CaseTransitionForm(request.POST or None, allowed_states=allowed)
    if form.is_valid():
        try:
            entry.transition_to(
                form.cleaned_data["to_state"],
                actor=request.user,
                reason=form.cleaned_data.get("reason", ""),
            )
            messages.success(request, "Case state updated.")
        except ValidationError as exc:
            CaseEvent.objects.create(
                entry=entry, actor=request.user,
                action=CaseEvent.Action.DENIED,
                detail=str(exc),
            )
            messages.error(request, str(exc))
    return redirect("cases:detail", pk=pk)


# ---------------------------------------------------------------------------
# Intervention Plan
# ---------------------------------------------------------------------------

@role_required(Role.SUPERVISOR, Role.ADMIN)
def intervention_create(request, entry_pk):
    entry = get_object_or_404(SERSEntry, pk=entry_pk)
    form  = InterventionPlanForm(request.POST or None)
    if form.is_valid():
        plan = form.save(commit=False)
        plan.entry = entry
        plan.save()
        CaseEvent.objects.create(
            entry=entry, actor=request.user,
            action=CaseEvent.Action.INTERVENTION,
            detail=(
                f"Intervention plan created: "
                f"{plan.get_plan_type_display()}, due {plan.due_date}."
            ),
        )
        messages.success(request, "Intervention plan created.")
        return redirect("cases:detail", pk=entry_pk)
    return render(request, "cases/intervention_form.html",
                  {"form": form, "entry": entry})


@role_required(Role.SUPERVISOR, Role.ADMIN)
def intervention_complete(request, plan_pk):
    plan = get_object_or_404(InterventionPlan, pk=plan_pk)
    if request.method == "POST":
        plan.mark_completed(actor=request.user)
        messages.success(request, "Intervention marked completed.")
    return redirect("cases:detail", pk=plan.entry_id)


# ---------------------------------------------------------------------------
# SERS Policy (Admin only)
# ---------------------------------------------------------------------------

@role_required(Role.ADMIN)
def sers_policy_edit(request):
    policy = SERSPolicy.current()
    form   = SERSPolicyForm(request.POST or None, instance=policy)
    if form.is_valid():
        obj = form.save(commit=False)
        obj.updated_by = request.user
        obj.save()
        messages.success(request, "SERS policy updated.")
        return redirect("cases:sers_policy")
    return render(request, "cases/sers_policy.html", {"form": form, "policy": policy})


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

@role_required(Role.SUPERVISOR, Role.ADMIN)
def export_cases_csv(request):
    qs = _scoped_entries(request.user).order_by("-created_at")
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="sers_cases.csv"'
    writer = csv.writer(response)
    writer.writerow([
        "id", "student_id", "student_name", "school", "region",
        "sers_score", "risk_level", "workflow_state",
        "absences", "grade_drop", "behavior", "wellbeing",
        "period", "operator", "created_at",
    ])
    for e in qs:
        writer.writerow([
            e.pk, e.student.external_id, e.student.display_name,
            e.student.school, e.student.region,
            e.sers_score, e.risk_level, e.workflow_state,
            e.unexcused_absences, e.grade_drop_points,
            e.disciplinary_flags, e.wellbeing_score,
            e.period_label, e.operator.username,
            e.created_at.strftime("%Y-%m-%d %H:%M"),
        ])
    return response
