"""Dashboard views.

Three entry points:
- ``home``: routes a logged-in user to the dashboard that matches their role.
- ``admin_kpis``: system-wide KPIs for the program Admin (Prompt 4).
- ``supervisor_queue``: filtered Case List for Supervisors showing only
  students in Assessment or Intervention Planning.
"""

from __future__ import annotations

from collections import Counter

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.shortcuts import redirect, render

from accounts.models import Role
from accounts.permissions import role_required
from cases.models import (
    Appointment,
    CaseEvent,
    RiskLevel,
    RiskPolicy,
    StressAssessment,
    WorkflowState,
)


@login_required
def home(request):
    user = request.user
    if user.is_program_admin:
        return redirect("dashboard:admin_kpis")
    if user.is_supervisor:
        return redirect("dashboard:supervisor_queue")
    # Operators land on their case list directly.
    return redirect("cases:list")


@role_required(Role.ADMIN)
def admin_kpis(request):
    qs = StressAssessment.objects.all()
    total = qs.count()
    closed = qs.filter(workflow_state=WorkflowState.CLOSED).count()
    workflow_completion_rate = (closed / total * 100) if total else 0.0

    denied = CaseEvent.objects.filter(action=CaseEvent.Action.DENIED).count()
    intakes = CaseEvent.objects.filter(action=CaseEvent.Action.INTAKE).count()
    # Admin dashboard KPI: fraction of intakes that passed validation
    # (``intakes`` only contains rows that were successfully saved, so the
    # pass rate is intakes / (intakes + denied form submissions)).
    validation_pass_rate = (
        intakes / (intakes + denied) * 100 if (intakes + denied) else 100.0
    )

    by_region: Counter[str] = Counter()
    by_school: Counter[str] = Counter()
    for a in qs.filter(risk_level=RiskLevel.HIGH).select_related("student"):
        by_region[a.student.region or "—"] += 1
        by_school[a.student.school or "—"] += 1

    appt_total = Appointment.objects.count()
    appt_missed = Appointment.objects.filter(status=Appointment.Status.MISSED).count()
    reminders_sent = CaseEvent.objects.filter(
        action=CaseEvent.Action.REMINDER
    ).count()

    avg_score = qs.aggregate(avg=Avg("total_score"))["avg"] or 0
    policy = RiskPolicy.current()
    state_counts_map = dict(
        qs.values_list("workflow_state").annotate(n=Count("id"))
    )
    risk_counts_map = dict(
        qs.values_list("risk_level").annotate(n=Count("id"))
    )
    state_counts = [
        (label, state_counts_map.get(value, 0))
        for value, label in WorkflowState.choices
    ]
    risk_counts = [
        (label, risk_counts_map.get(value, 0))
        for value, label in RiskLevel.choices
    ]

    return render(
        request,
        "dashboard/admin_kpis.html",
        {
            "total": total,
            "closed": closed,
            "workflow_completion_rate": round(workflow_completion_rate, 1),
            "validation_pass_rate": round(validation_pass_rate, 1),
            "denied": denied,
            "by_region": by_region.most_common(),
            "by_school": by_school.most_common(),
            "appt_total": appt_total,
            "appt_missed": appt_missed,
            "reminders_sent": reminders_sent,
            "avg_score": round(float(avg_score), 1),
            "policy": policy,
            "state_counts": state_counts,
            "risk_counts": risk_counts,
        },
    )


@role_required(Role.SUPERVISOR, Role.ADMIN)
def supervisor_queue(request):
    qs = (
        StressAssessment.objects.filter(
            workflow_state__in=(WorkflowState.ASSESSMENT, WorkflowState.INTERVENTION)
        )
        .select_related("student", "operator")
        .order_by("-risk_level", "-total_score")
    )
    high_risk = qs.filter(risk_level=RiskLevel.HIGH)
    missed_appointments = Appointment.objects.filter(
        status=Appointment.Status.MISSED
    ).select_related("assessment", "assessment__student")[:20]
    return render(
        request,
        "dashboard/supervisor_queue.html",
        {
            "assessments": qs,
            "high_risk": high_risk,
            "missed_appointments": missed_appointments,
            "policy": RiskPolicy.current(),
        },
    )
