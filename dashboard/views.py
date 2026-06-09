from __future__ import annotations

from collections import Counter

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.shortcuts import redirect, render

from accounts.models import Role
from accounts.permissions import role_required
from cases.models import (
    CaseEvent, InterventionPlan, RiskLevel,
    SERSEntry, SERSPolicy, WorkflowState,
)


@login_required
def home(request):
    user = request.user
    if user.is_program_admin:
        return redirect("dashboard:admin_kpis")
    if user.is_supervisor:
        return redirect("dashboard:supervisor_queue")
    return redirect("cases:list")


@role_required(Role.ADMIN)
def admin_kpis(request):
    qs    = SERSEntry.objects.all()
    total = qs.count()
    closed = qs.filter(workflow_state=WorkflowState.CLOSED).count()
    completion_rate = (closed / total * 100) if total else 0.0

    denied   = CaseEvent.objects.filter(action=CaseEvent.Action.DENIED).count()
    security = CaseEvent.objects.filter(action=CaseEvent.Action.SECURITY).count()
    intakes  = CaseEvent.objects.filter(action=CaseEvent.Action.INTAKE).count()
    validation_pass_rate = (
        intakes / (intakes + denied) * 100 if (intakes + denied) else 100.0
    )

    by_region: Counter = Counter()
    by_school: Counter = Counter()
    for e in qs.filter(risk_level=RiskLevel.HIGH).select_related("student"):
        by_region[e.student.region or "—"] += 1
        by_school[e.student.school or "—"] += 1

    avg_score = qs.aggregate(avg=Avg("sers_score"))["avg"] or 0

    plan_total     = InterventionPlan.objects.count()
    plan_completed = InterventionPlan.objects.filter(
        status=InterventionPlan.PlanStatus.COMPLETED
    ).count()
    plan_completion = (plan_completed / plan_total * 100) if plan_total else 0.0

    state_counts_map = dict(
        qs.values_list("workflow_state").annotate(n=Count("id"))
    )
    risk_counts_map = dict(
        qs.values_list("risk_level").annotate(n=Count("id"))
    )
    state_counts = [(l, state_counts_map.get(v, 0)) for v, l in WorkflowState.choices]
    risk_counts  = [(l, risk_counts_map.get(v, 0))  for v, l in RiskLevel.choices]

    return render(request, "dashboard/admin_kpis.html", {
        "total":                total,
        "closed":               closed,
        "completion_rate":      round(completion_rate, 1),
        "validation_pass_rate": round(validation_pass_rate, 1),
        "denied":               denied,
        "security_events":      security,
        "by_region":            by_region.most_common(),
        "by_school":            by_school.most_common(),
        "avg_score":            round(float(avg_score), 1),
        "plan_total":           plan_total,
        "plan_completed":       plan_completed,
        "plan_completion":      round(plan_completion, 1),
        "state_counts":         state_counts,
        "risk_counts":          risk_counts,
        "policy":               SERSPolicy.current(),
    })


@role_required(Role.SUPERVISOR, Role.ADMIN)
def supervisor_queue(request):
    qs = (
        SERSEntry.objects.filter(
            workflow_state__in=(
                WorkflowState.ASSESSMENT,
                WorkflowState.INTERVENTION,
            )
        )
        .select_related("student", "operator")
        .order_by("-risk_level", "-sers_score")
    )
    high_risk = qs.filter(risk_level=RiskLevel.HIGH)
    overdue_plans = (
        InterventionPlan.objects.filter(
            status__in=(
                InterventionPlan.PlanStatus.PENDING,
                InterventionPlan.PlanStatus.ACTIVE,
            ),
        )
        .select_related("entry", "entry__student", "assigned_to")
    )
    return render(request, "dashboard/supervisor_queue.html", {
        "entries":       qs,
        "high_risk":     high_risk,
        "overdue_plans": overdue_plans,
        "policy":        SERSPolicy.current(),
    })
