"""Views for the case-management workflow.

The views are deliberately thin wrappers around the models: the
business logic (risk scoring, state machine, missed-appointment
reminders) lives on ``cases.models`` so that it can be exercised by
the test suite without going through HTTP.
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Iterable

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import Role
from accounts.permissions import role_required

from .forms import (
    AppointmentForm,
    CaseTransitionForm,
    RiskPolicyForm,
    StressAssessmentCSVUploadForm,
    StressAssessmentForm,
    StudentForm,
)
from .models import (
    ALLOWED_TRANSITIONS,
    Appointment,
    CaseEvent,
    RiskLevel,
    RiskPolicy,
    Student,
    StressAssessment,
    WorkflowState,
)

logger = logging.getLogger("wellbeing.cases")


# ---------------------------------------------------------------------------
# Role-scoped querysets ------------------------------------------------------
# ---------------------------------------------------------------------------
def _scoped_assessments(user) -> "models.QuerySet[StressAssessment]":  # type: ignore[name-defined]
    qs = StressAssessment.objects.select_related("student", "operator")
    if user.is_program_admin or user.is_supervisor:
        return qs
    if user.is_operator:
        # Operators see only their own submissions (and optionally their
        # school's assessments). We implement both rules with OR so the
        # collaboration still works across shifts.
        school = user.school or None
        base = qs.filter(operator=user)
        if school:
            base = base | qs.filter(student__school=school)
        return base.distinct()
    return qs.none()


# ---------------------------------------------------------------------------
# Listing and detail ---------------------------------------------------------
# ---------------------------------------------------------------------------
@login_required
def case_list(request):
    qs = _scoped_assessments(request.user).order_by("-created_at")
    state = request.GET.get("state") or ""
    risk = request.GET.get("risk") or ""
    if state:
        qs = qs.filter(workflow_state=state)
    if risk:
        qs = qs.filter(risk_level=risk)
    return render(
        request,
        "cases/case_list.html",
        {
            "assessments": qs[:500],
            "state_choices": WorkflowState.choices,
            "risk_choices": RiskLevel.choices,
            "selected_state": state,
            "selected_risk": risk,
        },
    )


@login_required
def case_detail(request, pk: int):
    assessment = get_object_or_404(_scoped_assessments(request.user), pk=pk)
    allowed = [
        (s, WorkflowState(s).label)
        for s in ALLOWED_TRANSITIONS.get(assessment.workflow_state, set())
    ]
    transition_form = CaseTransitionForm(allowed_states=allowed)
    appointment_form = AppointmentForm()
    return render(
        request,
        "cases/case_detail.html",
        {
            "assessment": assessment,
            "events": assessment.events.select_related("actor")[:50],
            "appointments": assessment.appointments.all(),
            "transition_form": transition_form,
            "appointment_form": appointment_form,
        },
    )


# ---------------------------------------------------------------------------
# Operator actions -----------------------------------------------------------
# ---------------------------------------------------------------------------
@role_required(Role.OPERATOR, Role.ADMIN)
def student_create(request):
    if request.method == "POST":
        form = StudentForm(request.POST)
        if form.is_valid():
            student = form.save()
            messages.success(request, f"Student {student.display_name} added.")
            return redirect("cases:assessment_create")
    else:
        form = StudentForm()
    return render(request, "cases/student_form.html", {"form": form})


@role_required(Role.OPERATOR, Role.ADMIN)
def assessment_create(request):
    if request.method == "POST":
        form = StressAssessmentForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    assessment = form.save(commit=False)
                    assessment.operator = request.user
                    assessment.save()
                    CaseEvent.objects.create(
                        assessment=assessment,
                        actor=request.user,
                        action=CaseEvent.Action.INTAKE,
                        to_state=assessment.workflow_state,
                        detail=(
                            f"Intake recorded. Risk level: "
                            f"{assessment.get_risk_level_display()}."
                        ),
                    )
            except ValidationError as exc:
                for field, errs in exc.message_dict.items():
                    for err in errs:
                        form.add_error(field, err)
            else:
                messages.success(
                    request,
                    f"Assessment saved. Risk level: "
                    f"{assessment.get_risk_level_display()}.",
                )
                return redirect("cases:detail", pk=assessment.pk)
    else:
        form = StressAssessmentForm()
    return render(request, "cases/assessment_form.html", {"form": form})


@role_required(Role.OPERATOR, Role.ADMIN)
def assessment_upload_csv(request):
    """Bulk-upload assessments from a CSV file.

    Bad rows are collected and reported back; the whole upload is
    aborted so the user doesn't end up with a half-loaded dataset.
    """

    errors: list[str] = []
    created = 0
    if request.method == "POST":
        form = StressAssessmentCSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            raw = form.cleaned_data["csv_file"].read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(raw))
            required = {
                "external_id",
                "academic_pressure",
                "social_anxiety",
                "home_environment",
            }
            missing = required.difference(reader.fieldnames or [])
            if missing:
                errors.append(
                    "CSV is missing required column(s): " + ", ".join(sorted(missing))
                )
            else:
                try:
                    with transaction.atomic():
                        for i, row in enumerate(reader, start=2):
                            err = _create_assessment_from_row(row, request.user)
                            if err:
                                errors.append(f"Row {i}: {err}")
                            else:
                                created += 1
                        if errors:
                            raise _Abort()
                except _Abort:
                    logger.warning(
                        "CSV upload aborted by %s: %s errors", request.user, len(errors)
                    )
                    created = 0
    else:
        form = StressAssessmentCSVUploadForm()
    if request.method == "POST" and not errors:
        messages.success(request, f"Uploaded {created} assessments.")
        return redirect("cases:list")
    return render(
        request,
        "cases/assessment_upload.html",
        {"form": form, "errors": errors, "created": created},
    )


class _Abort(Exception):
    """Internal sentinel used to roll back a CSV upload on first error."""


def _create_assessment_from_row(row: dict, user) -> str:
    ext_id = (row.get("external_id") or "").strip()
    if not ext_id:
        return "missing external_id."
    try:
        student = Student.objects.get(external_id=ext_id)
    except Student.DoesNotExist:
        return f"unknown student '{ext_id}'."
    try:
        ap = int(row["academic_pressure"])
        sa = int(row["social_anxiety"])
        he = int(row["home_environment"])
    except (KeyError, TypeError, ValueError):
        return "score columns must be integers."
    try:
        assessment = StressAssessment(
            student=student,
            operator=user,
            academic_pressure=ap,
            social_anxiety=sa,
            home_environment=he,
            notes=(row.get("notes") or "").strip(),
        )
        assessment.save()
    except ValidationError as exc:
        return "; ".join(
            f"{field}: {'; '.join(errs)}" for field, errs in exc.message_dict.items()
        )
    CaseEvent.objects.create(
        assessment=assessment,
        actor=user,
        action=CaseEvent.Action.INTAKE,
        to_state=assessment.workflow_state,
        detail=(
            "Intake from CSV upload."
            f" Risk level: {assessment.get_risk_level_display()}."
        ),
    )
    return ""


# ---------------------------------------------------------------------------
# Supervisor / admin actions -------------------------------------------------
# ---------------------------------------------------------------------------
@role_required(Role.SUPERVISOR, Role.ADMIN)
def case_transition(request, pk: int):
    assessment = get_object_or_404(StressAssessment, pk=pk)
    allowed = [
        (s, WorkflowState(s).label)
        for s in ALLOWED_TRANSITIONS.get(assessment.workflow_state, set())
    ]
    form = CaseTransitionForm(request.POST or None, allowed_states=allowed)
    if request.method == "POST":
        if form.is_valid():
            try:
                assessment.transition_to(
                    form.cleaned_data["to_state"],
                    actor=request.user,
                    reason=form.cleaned_data.get("reason", ""),
                )
            except ValidationError as exc:
                messages.error(request, str(exc))
                CaseEvent.objects.create(
                    assessment=assessment,
                    actor=request.user,
                    action=CaseEvent.Action.DENIED,
                    detail=str(exc),
                )
            else:
                messages.success(request, "Case state updated.")
        else:
            messages.error(request, "Invalid transition request.")
    return redirect("cases:detail", pk=assessment.pk)


@role_required(Role.SUPERVISOR, Role.ADMIN)
def appointment_create(request, pk: int):
    assessment = get_object_or_404(StressAssessment, pk=pk)
    form = AppointmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        appt = form.save(commit=False)
        appt.assessment = assessment
        appt.scheduled_by = request.user
        appt.save()
        CaseEvent.objects.create(
            assessment=assessment,
            actor=request.user,
            action=CaseEvent.Action.APPOINTMENT,
            detail=(
                f"Appointment scheduled for {appt.scheduled_for:%Y-%m-%d %H:%M}."
            ),
        )
        messages.success(request, "Appointment scheduled.")
    elif request.method == "POST":
        messages.error(request, "Invalid appointment details.")
    return redirect("cases:detail", pk=pk)


@role_required(Role.SUPERVISOR, Role.ADMIN)
def appointment_mark_missed(request, pk: int):
    appointment = get_object_or_404(Appointment, pk=pk)
    if request.method != "POST":
        raise PermissionDenied("POST required.")
    appointment.mark_missed(actor=request.user)
    messages.warning(
        request,
        "Appointment marked as missed; automatic reminder queued.",
    )
    return redirect("cases:detail", pk=appointment.assessment_id)


@role_required(Role.SUPERVISOR, Role.ADMIN)
def risk_policy_edit(request):
    policy = RiskPolicy.current()
    form = RiskPolicyForm(request.POST or None, instance=policy)
    if request.method == "POST" and form.is_valid():
        policy = form.save(commit=False)
        policy.updated_by = request.user
        policy.save()
        messages.success(
            request,
            f"High-Risk threshold updated to {policy.threshold}.",
        )
        return redirect("cases:risk_policy")
    return render(request, "cases/risk_policy.html", {"form": form, "policy": policy})


@login_required
def export_cases_csv(request):
    qs = _scoped_assessments(request.user)
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = (
        f'attachment; filename="cases-{timezone.now():%Y%m%d%H%M}.csv"'
    )
    writer = csv.writer(response)
    writer.writerow(
        [
            "case_id",
            "student",
            "school",
            "region",
            "workflow_state",
            "risk_level",
            "total_score",
            "academic_pressure",
            "social_anxiety",
            "home_environment",
            "created_at",
        ]
    )
    for a in qs:
        writer.writerow(
            [
                a.pk,
                a.student.display_name,
                a.student.school,
                a.student.region,
                a.workflow_state,
                a.risk_level,
                a.total_score,
                a.academic_pressure,
                a.social_anxiety,
                a.home_environment,
                a.created_at.isoformat(),
            ]
        )
    return response
