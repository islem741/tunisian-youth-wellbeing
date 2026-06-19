"""Strawberry query resolvers — all read operations for the GraphQL API.

Every resolver:
  1. Enforces role-based access via permissions.py classes.
  2. Applies the same scoping logic as cases/views._scoped_entries
     so that Operators only see their school's data.
  3. Supports optional filtering via the *FilterInput types.

Query list (12 total)
─────────────────────
  me                    — return the current user
  students              — list / filter students
  student               — single student by external_id
  sersEntries           — list / filter SERS entries
  sersEntry             — single SERS entry by id
  caseEvents            — audit trail for a single entry
  interventionPlans     — plans for a single entry
  sersPolicy            — current SERS scoring policy
  dashboardMetrics      — KPI numbers (Admin only)
  regionBreakdown       — high-risk count by region (Admin/Supervisor)
  schoolBreakdown       — high-risk count by school (Admin/Supervisor)
  supervisorQueue       — entries in ASSESSMENT or INTERVENTION state
"""

from __future__ import annotations

from typing import List, Optional

import strawberry
from django.db.models import Avg, Count, Q
from strawberry.types import Info

from .inputs import SERSEntryFilterInput, StudentFilterInput
from .permissions import IsAdmin, IsOperatorOrAbove, IsSupervisorOrAbove, _get_request
from .types import (
    CaseEventType,
    DashboardMetricsType,
    InterventionPlanType,
    RegionBreakdownType,
    SchoolBreakdownType,
    SERSEntryType,
    SERSPolicyType,
    StudentType,
    UserType,
    _map_case_event,
    _map_entry,
    _map_intervention,
    _map_student,
    _map_user,
)


# ---------------------------------------------------------------------------
# Scoping helper — mirrors cases/views._scoped_entries exactly
# ---------------------------------------------------------------------------

def _scoped_entries(user):
    from cases.models import SERSEntry
    qs = SERSEntry.objects.select_related("student", "operator")
    if user.is_program_admin or user.is_supervisor:
        return qs
    if user.is_operator:
        base = qs.filter(operator=user)
        if user.school:
            base = (base | qs.filter(student__school=user.school)).distinct()
        return base
    return qs.none()


def _apply_entry_filters(qs, f):
    if f is None or f is strawberry.UNSET:
        return qs
    if f.risk_level is not strawberry.UNSET and f.risk_level is not None:
        qs = qs.filter(risk_level=f.risk_level)
    if f.workflow_state is not strawberry.UNSET and f.workflow_state is not None:
        qs = qs.filter(workflow_state=f.workflow_state)
    if f.school is not strawberry.UNSET and f.school is not None:
        qs = qs.filter(student__school__icontains=f.school)
    if f.region is not strawberry.UNSET and f.region is not None:
        qs = qs.filter(student__region__icontains=f.region)
    if f.operator_id is not strawberry.UNSET and f.operator_id is not None:
        qs = qs.filter(operator_id=int(f.operator_id))
    if f.created_after is not strawberry.UNSET and f.created_after is not None:
        qs = qs.filter(created_at__date__gte=f.created_after)
    if f.created_before is not strawberry.UNSET and f.created_before is not None:
        qs = qs.filter(created_at__date__lte=f.created_before)
    return qs


# ---------------------------------------------------------------------------
# Query class
# ---------------------------------------------------------------------------

@strawberry.type
class Query:

    # ── 1. me ──────────────────────────────────────────────────────────────

    @strawberry.field(
        permission_classes=[IsOperatorOrAbove],
        description="Return the currently authenticated user.",
    )
    def me(self, info: Info) -> UserType:
        return _map_user(_get_request(info).user)

    # ── 2. students ────────────────────────────────────────────────────────

    @strawberry.field(
        permission_classes=[IsOperatorOrAbove],
        description=(
            "List students. Operators see only their school's students. "
            "Supports optional filtering by school, region, gender, grade."
        ),
    )
    def students(
        self,
        info: Info,
        filter: Optional[StudentFilterInput] = strawberry.UNSET,
    ) -> List[StudentType]:
        from cases.models import Student

        user = _get_request(info).user
        qs = Student.objects.all()

        # Scope Operators to their school
        if user.is_operator and user.school:
            qs = qs.filter(school=user.school)

        if filter is not strawberry.UNSET and filter is not None:
            if filter.school is not strawberry.UNSET and filter.school is not None:
                qs = qs.filter(school__icontains=filter.school)
            if filter.region is not strawberry.UNSET and filter.region is not None:
                qs = qs.filter(region__icontains=filter.region)
            if filter.gender is not strawberry.UNSET and filter.gender is not None:
                qs = qs.filter(gender=filter.gender)
            if filter.grade is not strawberry.UNSET and filter.grade is not None:
                qs = qs.filter(grade__icontains=filter.grade)

        return [_map_student(s) for s in qs.order_by("last_name", "first_name")]

    # ── 3. student (single) ────────────────────────────────────────────────

    @strawberry.field(
        permission_classes=[IsOperatorOrAbove],
        description="Fetch a single student by their opaque external_id.",
    )
    def student(
        self, info: Info, external_id: str
    ) -> Optional[StudentType]:
        from cases.models import Student

        user = _get_request(info).user
        try:
            s = Student.objects.get(external_id=external_id)
        except Student.DoesNotExist:
            return None

        # Operators: only their school
        if user.is_operator and user.school and s.school != user.school:
            return None

        return _map_student(s)

    # ── 4. sersEntries ─────────────────────────────────────────────────────

    @strawberry.field(
        permission_classes=[IsOperatorOrAbove],
        description=(
            "List SERS entries. Scoped by role (Operators see only their school). "
            "Supports filtering by risk_level, workflow_state, school, region, "
            "operator_id, created_after, created_before."
        ),
    )
    def sers_entries(
        self,
        info: Info,
        filter: Optional[SERSEntryFilterInput] = strawberry.UNSET,
    ) -> List[SERSEntryType]:
        user = _get_request(info).user
        qs   = _scoped_entries(user)
        qs   = _apply_entry_filters(qs, filter)
        return [_map_entry(e) for e in qs.order_by("-created_at")]

    # ── 5. sersEntry (single) ──────────────────────────────────────────────

    @strawberry.field(
        permission_classes=[IsOperatorOrAbove],
        description="Fetch a single SERS entry by id. Respects scoping rules.",
    )
    def sers_entry(
        self, info: Info, id: strawberry.ID
    ) -> Optional[SERSEntryType]:
        user = _get_request(info).user
        qs   = _scoped_entries(user)
        try:
            entry = qs.get(pk=int(id))
        except Exception:
            return None
        return _map_entry(entry)

    # ── 6. caseEvents ─────────────────────────────────────────────────────

    @strawberry.field(
        permission_classes=[IsOperatorOrAbove],
        description=(
            "Return the full audit trail for a single SERS entry. "
            "Operators are subject to the same scoping rules as sersEntry."
        ),
    )
    def case_events(
        self, info: Info, entry_id: strawberry.ID
    ) -> List[CaseEventType]:
        from cases.models import CaseEvent

        user = _get_request(info).user
        # Verify the caller can see the parent entry
        scoped = _scoped_entries(user).filter(pk=int(entry_id))
        if not scoped.exists():
            return []

        events = (
            CaseEvent.objects.filter(entry_id=int(entry_id))
            .select_related("actor")
            .order_by("-created_at")
        )
        return [_map_case_event(e) for e in events]

    # ── 7. interventionPlans ───────────────────────────────────────────────

    @strawberry.field(
        permission_classes=[IsOperatorOrAbove],
        description="Return intervention plans attached to a SERS entry.",
    )
    def intervention_plans(
        self, info: Info, entry_id: strawberry.ID
    ) -> List[InterventionPlanType]:
        from cases.models import InterventionPlan

        user = _get_request(info).user
        scoped = _scoped_entries(user).filter(pk=int(entry_id))
        if not scoped.exists():
            return []

        plans = (
            InterventionPlan.objects.filter(entry_id=int(entry_id))
            .select_related("assigned_to")
            .order_by("due_date")
        )
        return [_map_intervention(p) for p in plans]

    # ── 8. sersPolicy ─────────────────────────────────────────────────────

    @strawberry.field(
        permission_classes=[IsOperatorOrAbove],
        description="Return the current SERS scoring policy (weights and thresholds).",
    )
    def sers_policy(self, info: Info) -> SERSPolicyType:
        from cases.models import SERSPolicy

        p = SERSPolicy.current()
        return SERSPolicyType(
            id=strawberry.ID(str(p.pk)),
            absence_weight=p.absence_weight,
            grade_drop_weight=p.grade_drop_weight,
            behavior_weight=p.behavior_weight,
            wellbeing_weight=p.wellbeing_weight,
            high_threshold=p.high_threshold,
            medium_threshold=p.medium_threshold,
            updated_at=p.updated_at,
        )

    # ── 9. dashboardMetrics ────────────────────────────────────────────────

    @strawberry.field(
        permission_classes=[IsAdmin],
        description=(
            "Return KPI dashboard metrics. Admin only. "
            "Mirrors the logic in dashboard/views.admin_kpis."
        ),
    )
    def dashboard_metrics(self, info: Info) -> DashboardMetricsType:
        from cases.models import CaseEvent, InterventionPlan, RiskLevel, SERSEntry, WorkflowState

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
        avg_score   = qs.aggregate(avg=Avg("sers_score"))["avg"] or 0.0
        plan_total  = InterventionPlan.objects.count()
        plan_done   = InterventionPlan.objects.filter(
            status=InterventionPlan.PlanStatus.COMPLETED
        ).count()
        plan_rate   = (plan_done / plan_total * 100) if plan_total else 0.0

        high_count   = qs.filter(risk_level=RiskLevel.HIGH).count()
        medium_count = qs.filter(risk_level=RiskLevel.MEDIUM).count()
        low_count    = qs.filter(risk_level=RiskLevel.LOW).count()

        return DashboardMetricsType(
            total_entries=total,
            closed_entries=closed,
            completion_rate=round(completion_rate, 1),
            validation_pass_rate=round(validation_pass_rate, 1),
            security_event_count=security,
            avg_sers_score=round(float(avg_score), 1),
            plan_total=plan_total,
            plan_completed=plan_done,
            plan_completion_rate=round(plan_rate, 1),
            high_risk_count=high_count,
            medium_risk_count=medium_count,
            low_risk_count=low_count,
        )

    # ── 10. regionBreakdown ────────────────────────────────────────────────

    @strawberry.field(
        permission_classes=[IsSupervisorOrAbove],
        description="Return count of HIGH-risk entries grouped by region.",
    )
    def region_breakdown(self, info: Info) -> List[RegionBreakdownType]:
        from cases.models import RiskLevel, SERSEntry

        rows = (
            SERSEntry.objects.filter(risk_level=RiskLevel.HIGH)
            .values("student__region")
            .annotate(n=Count("id"))
            .order_by("-n")
        )
        return [
            RegionBreakdownType(region=r["student__region"] or "—", count=r["n"])
            for r in rows
        ]

    # ── 11. schoolBreakdown ────────────────────────────────────────────────

    @strawberry.field(
        permission_classes=[IsSupervisorOrAbove],
        description="Return count of HIGH-risk entries grouped by school.",
    )
    def school_breakdown(self, info: Info) -> List[SchoolBreakdownType]:
        from cases.models import RiskLevel, SERSEntry

        rows = (
            SERSEntry.objects.filter(risk_level=RiskLevel.HIGH)
            .values("student__school")
            .annotate(n=Count("id"))
            .order_by("-n")
        )
        return [
            SchoolBreakdownType(school=r["student__school"] or "—", count=r["n"])
            for r in rows
        ]

    # ── 12. supervisorQueue ────────────────────────────────────────────────

    @strawberry.field(
        permission_classes=[IsSupervisorOrAbove],
        description=(
            "Return entries currently in ASSESSMENT or INTERVENTION state, "
            "ordered by risk severity. Mirrors the Supervisor queue view."
        ),
    )
    def supervisor_queue(self, info: Info) -> List[SERSEntryType]:
        from cases.models import SERSEntry, WorkflowState

        qs = (
            SERSEntry.objects.filter(
                workflow_state__in=(
                    WorkflowState.ASSESSMENT,
                    WorkflowState.INTERVENTION,
                )
            )
            .select_related("student", "operator")
            .order_by("-sers_score")
        )
        return [_map_entry(e) for e in qs]
