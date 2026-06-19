"""Strawberry input types — one per mutation or filter operation.

Input types are validated at the GraphQL layer before any ORM call is made.
Where the underlying model already has a ``clean()`` method (e.g. SERSEntry),
model-level validation is also invoked inside the mutation resolver so there
is no duplication of rules.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

import strawberry


# ---------------------------------------------------------------------------
# Student inputs
# ---------------------------------------------------------------------------

@strawberry.input
class CreateStudentInput:
    external_id: str
    first_name:  str
    last_name:   str
    age:         int
    gender:      str        # "F" | "M" | "O"
    grade:       str        = ""
    school:      str        = ""
    region:      str        = ""


# ---------------------------------------------------------------------------
# SERS Entry inputs
# ---------------------------------------------------------------------------

@strawberry.input
class CreateSERSEntryInput:
    student_external_id:  str
    period_label:         str        = ""
    unexcused_absences:   int        = 0
    grade_drop_points:    int        = 0
    disciplinary_flags:   int        = 0
    wellbeing_score:      int        = 5
    notes:                str        = ""


@strawberry.input
class TransitionCaseInput:
    entry_id:  strawberry.ID
    to_state:  str           # must be a valid WorkflowState value
    reason:    str           = ""


# ---------------------------------------------------------------------------
# Intervention Plan inputs
# ---------------------------------------------------------------------------

@strawberry.input
class CreateInterventionPlanInput:
    entry_id:      strawberry.ID
    plan_type:     str            # PlanType choice value
    assigned_to_id: strawberry.ID
    due_date:      date
    notes:         str            = ""


@strawberry.input
class CompleteInterventionPlanInput:
    plan_id: strawberry.ID


# ---------------------------------------------------------------------------
# SERS Policy input (Admin only)
# ---------------------------------------------------------------------------

@strawberry.input
class UpdateSERSPolicyInput:
    absence_weight:    Optional[int] = strawberry.UNSET
    grade_drop_weight: Optional[int] = strawberry.UNSET
    behavior_weight:   Optional[int] = strawberry.UNSET
    wellbeing_weight:  Optional[int] = strawberry.UNSET
    high_threshold:    Optional[int] = strawberry.UNSET
    medium_threshold:  Optional[int] = strawberry.UNSET


# ---------------------------------------------------------------------------
# Filter inputs
# ---------------------------------------------------------------------------

@strawberry.input
class SERSEntryFilterInput:
    risk_level:      Optional[str]  = strawberry.UNSET  # low | medium | high
    workflow_state:  Optional[str]  = strawberry.UNSET  # intake | assessment | …
    school:          Optional[str]  = strawberry.UNSET
    region:          Optional[str]  = strawberry.UNSET
    operator_id:     Optional[strawberry.ID] = strawberry.UNSET
    created_after:   Optional[date] = strawberry.UNSET
    created_before:  Optional[date] = strawberry.UNSET


@strawberry.input
class StudentFilterInput:
    school:  Optional[str] = strawberry.UNSET
    region:  Optional[str] = strawberry.UNSET
    gender:  Optional[str] = strawberry.UNSET
    grade:   Optional[str] = strawberry.UNSET
