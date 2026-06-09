"""Strawberry mutations — all write operations for the GraphQL API.

Every mutation:
  1. Enforces role-based access via permissions.py classes.
  2. Delegates business logic to existing model methods or services —
     no business rules are duplicated here.
  3. Returns a union of success payload | error payload so callers
     always receive a typed response, never an unhandled exception.

Mutation list
─────────────
  createStudent           — Operator / Admin
  createSERSEntry         — Operator / Admin      (reuses SERSEntry.save())
  transitionCase          — Supervisor / Admin    (reuses entry.transition_to())
  createInterventionPlan  — Supervisor / Admin
  completeInterventionPlan— Supervisor / Admin    (reuses plan.mark_completed())
  updateSERSPolicy        — Admin only            (reuses SERSPolicy.clean())
"""

from __future__ import annotations

from typing import Annotated, Union

import strawberry
from django.core.exceptions import ValidationError
from strawberry.types import Info

from .inputs import (
    CompleteInterventionPlanInput,
    CreateInterventionPlanInput,
    CreateSERSEntryInput,
    CreateStudentInput,
    TransitionCaseInput,
    UpdateSERSPolicyInput,
)
from .permissions import IsAdmin, IsOperatorOrAbove, IsSupervisorOrAbove, _get_request
from .types import (
    InterventionPlanType,
    SERSEntryType,
    SERSPolicyType,
    StudentType,
    _map_entry,
    _map_intervention,
    _map_student,
)


# ---------------------------------------------------------------------------
# Shared error type
# ---------------------------------------------------------------------------

@strawberry.type
class MutationError:
    message: str
    field:   str = ""   # populated when the error is field-specific


# ---------------------------------------------------------------------------
# Per-mutation result unions
# ---------------------------------------------------------------------------

CreateStudentResult = Annotated[
    Union[StudentType, MutationError],
    strawberry.union("CreateStudentResult"),
]

CreateSERSEntryResult = Annotated[
    Union[SERSEntryType, MutationError],
    strawberry.union("CreateSERSEntryResult"),
]

TransitionCaseResult = Annotated[
    Union[SERSEntryType, MutationError],
    strawberry.union("TransitionCaseResult"),
]

CreateInterventionPlanResult = Annotated[
    Union[InterventionPlanType, MutationError],
    strawberry.union("CreateInterventionPlanResult"),
]

CompleteInterventionPlanResult = Annotated[
    Union[InterventionPlanType, MutationError],
    strawberry.union("CompleteInterventionPlanResult"),
]

UpdateSERSPolicyResult = Annotated[
    Union[SERSPolicyType, MutationError],
    strawberry.union("UpdateSERSPolicyResult"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _map_sers_policy(p) -> SERSPolicyType:
    from .types import SERSPolicyType as _T
    return _T(
        id=strawberry.ID(str(p.pk)),
        absence_weight=p.absence_weight,
        grade_drop_weight=p.grade_drop_weight,
        behavior_weight=p.behavior_weight,
        wellbeing_weight=p.wellbeing_weight,
        high_threshold=p.high_threshold,
        medium_threshold=p.medium_threshold,
        updated_at=p.updated_at,
    )


# ---------------------------------------------------------------------------
# Mutation class
# ---------------------------------------------------------------------------

@strawberry.type
class Mutation:

    # ── 1. Create student ──────────────────────────────────────────────────

    @strawberry.mutation(
        permission_classes=[IsOperatorOrAbove],
        description="Create a new Student record. Available to Operators and Admins.",
    )
    def create_student(
        self, info: Info, data: CreateStudentInput
    ) -> CreateStudentResult:
        from cases.models import Student

        if Student.objects.filter(external_id=data.external_id).exists():
            return MutationError(
                message=f"A student with external_id '{data.external_id}' already exists.",
                field="external_id",
            )

        VALID_GENDERS = ("F", "M", "O")
        if data.gender not in VALID_GENDERS:
            return MutationError(
                message=f"gender must be one of {VALID_GENDERS}.",
                field="gender",
            )
        if not (10 <= data.age <= 20):
            return MutationError(
                message="age must be between 10 and 20.",
                field="age",
            )

        student = Student.objects.create(
            external_id=data.external_id,
            first_name=data.first_name,
            last_name=data.last_name,
            age=data.age,
            gender=data.gender,
            grade=data.grade,
            school=data.school,
            region=data.region,
        )
        return _map_student(student)

    # ── 2. Create SERS entry ───────────────────────────────────────────────

    @strawberry.mutation(
        permission_classes=[IsOperatorOrAbove],
        description=(
            "Submit a new SERS entry for a student. "
            "The SERS score and risk level are computed automatically. "
            "HIGH-risk entries are auto-promoted to Assessment state."
        ),
    )
    def create_sers_entry(
        self, info: Info, data: CreateSERSEntryInput
    ) -> CreateSERSEntryResult:
        from cases.models import CaseEvent, SERSEntry, Student

        try:
            student = Student.objects.get(external_id=data.student_external_id)
        except Student.DoesNotExist:
            return MutationError(
                message=f"No student with external_id '{data.student_external_id}'.",
                field="student_external_id",
            )

        try:
            entry = SERSEntry(
                student=student,
                operator=_get_request(info).user,
                period_label=data.period_label,
                unexcused_absences=data.unexcused_absences,
                grade_drop_points=data.grade_drop_points,
                disciplinary_flags=data.disciplinary_flags,
                wellbeing_score=data.wellbeing_score,
                notes=data.notes,
            )
            entry.save()  # triggers full_clean() + SERS computation
        except ValidationError as exc:
            msgs = "; ".join(
                f"{f}: {', '.join(errs)}"
                for f, errs in (exc.message_dict.items()
                                if hasattr(exc, "message_dict")
                                else {"__all__": exc.messages}.items())
            )
            return MutationError(message=msgs)

        CaseEvent.objects.create(
            entry=entry,
            actor=_get_request(info).user,
            action=CaseEvent.Action.INTAKE,
            to_state=entry.workflow_state,
            detail=(
                f"GraphQL entry. SERS={entry.sers_score} "
                f"({entry.get_risk_level_display()}). "
                f"{entry.risk_explanation}"
            ),
        )
        return _map_entry(entry)

    # ── 3. Transition case ─────────────────────────────────────────────────

    @strawberry.mutation(
        permission_classes=[IsSupervisorOrAbove],
        description=(
            "Move a case to a new workflow state. "
            "Invalid transitions are rejected with a structured error. "
            "Every successful transition is logged as a CaseEvent."
        ),
    )
    def transition_case(
        self, info: Info, data: TransitionCaseInput
    ) -> TransitionCaseResult:
        from cases.models import SERSEntry

        try:
            entry = SERSEntry.objects.select_related("student", "operator").get(
                pk=int(data.entry_id)
            )
        except SERSEntry.DoesNotExist:
            return MutationError(message=f"No SERS entry with id {data.entry_id}.")

        try:
            entry.transition_to(
                data.to_state,
                actor=_get_request(info).user,
                reason=data.reason,
            )
        except ValidationError as exc:
            return MutationError(message=str(exc.message))

        entry.refresh_from_db()
        return _map_entry(entry)

    # ── 4. Create intervention plan ────────────────────────────────────────

    @strawberry.mutation(
        permission_classes=[IsSupervisorOrAbove],
        description="Attach an intervention plan to a SERS entry.",
    )
    def create_intervention_plan(
        self, info: Info, data: CreateInterventionPlanInput
    ) -> CreateInterventionPlanResult:
        from django.contrib.auth import get_user_model

        from cases.models import CaseEvent, InterventionPlan, SERSEntry

        User = get_user_model()

        try:
            entry = SERSEntry.objects.get(pk=int(data.entry_id))
        except SERSEntry.DoesNotExist:
            return MutationError(message=f"No SERS entry with id {data.entry_id}.")

        try:
            assigned_to = User.objects.get(pk=int(data.assigned_to_id))
        except User.DoesNotExist:
            return MutationError(
                message=f"No user with id {data.assigned_to_id}.",
                field="assigned_to_id",
            )

        valid_types = [c[0] for c in InterventionPlan.PlanType.choices]
        if data.plan_type not in valid_types:
            return MutationError(
                message=f"plan_type must be one of {valid_types}.",
                field="plan_type",
            )

        plan = InterventionPlan.objects.create(
            entry=entry,
            plan_type=data.plan_type,
            assigned_to=assigned_to,
            due_date=data.due_date,
            notes=data.notes,
        )
        CaseEvent.objects.create(
            entry=entry,
            actor=_get_request(info).user,
            action=CaseEvent.Action.INTERVENTION,
            detail=(
                f"GraphQL intervention plan created: "
                f"{plan.get_plan_type_display()}, due {plan.due_date}."
            ),
        )
        return _map_intervention(plan)

    # ── 5. Complete intervention plan ──────────────────────────────────────

    @strawberry.mutation(
        permission_classes=[IsSupervisorOrAbove],
        description="Mark an intervention plan as completed.",
    )
    def complete_intervention_plan(
        self, info: Info, data: CompleteInterventionPlanInput
    ) -> CompleteInterventionPlanResult:
        from cases.models import InterventionPlan

        try:
            plan = InterventionPlan.objects.select_related(
                "entry", "assigned_to"
            ).get(pk=int(data.plan_id))
        except InterventionPlan.DoesNotExist:
            return MutationError(message=f"No intervention plan with id {data.plan_id}.")

        plan.mark_completed(actor=_get_request(info).user)
        plan.refresh_from_db()
        return _map_intervention(plan)

    # ── 6. Update SERS policy (Admin only) ─────────────────────────────────

    @strawberry.mutation(
        permission_classes=[IsAdmin],
        description=(
            "Update the SERS scoring policy (weights and thresholds). "
            "Admin only. Validates that medium_threshold < high_threshold."
        ),
    )
    def update_sers_policy(
        self, info: Info, data: UpdateSERSPolicyInput
    ) -> UpdateSERSPolicyResult:
        from cases.models import SERSPolicy

        policy = SERSPolicy.current()
        fields_map = {
            "absence_weight":    "absence_weight",
            "grade_drop_weight": "grade_drop_weight",
            "behavior_weight":   "behavior_weight",
            "wellbeing_weight":  "wellbeing_weight",
            "high_threshold":    "high_threshold",
            "medium_threshold":  "medium_threshold",
        }
        for attr, model_field in fields_map.items():
            val = getattr(data, attr, strawberry.UNSET)
            if val is not strawberry.UNSET and val is not None:
                setattr(policy, model_field, val)

        policy.updated_by = _get_request(info).user
        try:
            policy.full_clean()
        except ValidationError as exc:
            msgs = "; ".join(exc.messages)
            return MutationError(message=msgs)

        policy.save()
        return _map_sers_policy(policy)
