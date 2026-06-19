"""Strawberry output types — one per domain model.

All types are read-only projections of existing Django ORM models.
No ORM logic lives here; types only declare what fields are exposed
and delegate any computation back to the model methods.
"""

from __future__ import annotations

import enum
from datetime import date, datetime
from typing import List, Optional

import strawberry


# ---------------------------------------------------------------------------
# Enums — mirror models.TextChoices exactly so clients get typed strings
# ---------------------------------------------------------------------------

@strawberry.enum
class RiskLevelEnum(enum.Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"


@strawberry.enum
class WorkflowStateEnum(enum.Enum):
    INTAKE       = "intake"
    ASSESSMENT   = "assessment"
    INTERVENTION = "intervention"
    FOLLOW_UP    = "follow_up"
    CLOSED       = "closed"


@strawberry.enum
class GenderEnum(enum.Enum):
    FEMALE = "F"
    MALE   = "M"
    OTHER  = "O"


@strawberry.enum
class PlanTypeEnum(enum.Enum):
    PARENT_MEETING = "parent_meeting"
    TUTORING       = "tutoring"
    COUNSELING     = "counseling"
    REFERRAL       = "referral"
    OTHER          = "other"


@strawberry.enum
class PlanStatusEnum(enum.Enum):
    PENDING   = "pending"
    ACTIVE    = "active"
    COMPLETED = "completed"
    ESCALATED = "escalated"


@strawberry.enum
class CaseActionEnum(enum.Enum):
    INTAKE       = "intake"
    STATE_CHANGE = "state_change"
    INTERVENTION = "intervention"
    REMINDER     = "reminder"
    NOTE         = "note"
    DENIED       = "denied"
    SECURITY     = "security"


@strawberry.enum
class UserRoleEnum(enum.Enum):
    OPERATOR   = "operator"
    SUPERVISOR = "supervisor"
    ADMIN      = "admin"


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------

@strawberry.type
class UserType:
    id:         strawberry.ID
    username:   str
    first_name: str
    last_name:  str
    role:       str
    school:     str
    region:     str

    @strawberry.field
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


@strawberry.type
class StudentType:
    id:          strawberry.ID
    external_id: str
    first_name:  str
    last_name:   str
    age:         int
    gender:      str
    grade:       str
    school:      str
    region:      str
    created_at:  datetime

    @strawberry.field
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


@strawberry.type
class CaseEventType:
    id:          strawberry.ID
    action:      str
    from_state:  str
    to_state:    str
    detail:      str
    created_at:  datetime
    actor:       Optional[UserType]

    @strawberry.field
    def human_summary(self) -> str:
        actor_name = (
            f"{self.actor.first_name} {self.actor.last_name}".strip()
            if self.actor else "System"
        )
        return f"{actor_name}: {self.detail or self.action}"


@strawberry.type
class InterventionPlanType:
    id:          strawberry.ID
    plan_type:   str
    status:      str
    due_date:    date
    notes:       str
    created_at:  datetime
    updated_at:  datetime
    assigned_to: Optional[UserType]


@strawberry.type
class SERSEntryType:
    id:                  strawberry.ID
    period_label:        str
    unexcused_absences:  int
    grade_drop_points:   int
    disciplinary_flags:  int
    wellbeing_score:     int
    notes:               str
    sers_score:          int
    risk_level:          str
    risk_explanation:    str
    workflow_state:      str
    created_at:          datetime
    updated_at:          datetime
    student:             StudentType
    operator:            UserType

    @strawberry.field
    def events(self) -> List[CaseEventType]:
        from cases.models import SERSEntry as _Entry
        entry = _Entry.objects.prefetch_related("events__actor").get(pk=int(self.id))
        return [_map_case_event(e) for e in entry.events.all()]

    @strawberry.field
    def interventions(self) -> List[InterventionPlanType]:
        from cases.models import SERSEntry as _Entry
        entry = _Entry.objects.prefetch_related("interventions__assigned_to").get(
            pk=int(self.id)
        )
        return [_map_intervention(p) for p in entry.interventions.all()]


@strawberry.type
class SERSPolicyType:
    id:                 strawberry.ID
    absence_weight:     int
    grade_drop_weight:  int
    behavior_weight:    int
    wellbeing_weight:   int
    high_threshold:     int
    medium_threshold:   int
    updated_at:         datetime


@strawberry.type
class DashboardMetricsType:
    total_entries:        int
    closed_entries:       int
    completion_rate:      float
    validation_pass_rate: float
    security_event_count: int
    avg_sers_score:       float
    plan_total:           int
    plan_completed:       int
    plan_completion_rate: float
    high_risk_count:      int
    medium_risk_count:    int
    low_risk_count:       int


@strawberry.type
class RegionBreakdownType:
    region: str
    count:  int


@strawberry.type
class SchoolBreakdownType:
    school: str
    count:  int


# ---------------------------------------------------------------------------
# Mapper helpers — convert ORM instances to Strawberry types
# ---------------------------------------------------------------------------

def _map_user(user) -> UserType:
    return UserType(
        id=strawberry.ID(str(user.pk)),
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        school=getattr(user, "school", ""),
        region=getattr(user, "region", ""),
    )


def _map_student(s) -> StudentType:
    return StudentType(
        id=strawberry.ID(str(s.pk)),
        external_id=s.external_id,
        first_name=s.first_name,
        last_name=s.last_name,
        age=s.age,
        gender=s.gender,
        grade=s.grade,
        school=s.school,
        region=s.region,
        created_at=s.created_at,
    )


def _map_case_event(e) -> CaseEventType:
    return CaseEventType(
        id=strawberry.ID(str(e.pk)),
        action=e.action,
        from_state=e.from_state,
        to_state=e.to_state,
        detail=e.detail,
        created_at=e.created_at,
        actor=_map_user(e.actor) if e.actor else None,
    )


def _map_intervention(p) -> InterventionPlanType:
    return InterventionPlanType(
        id=strawberry.ID(str(p.pk)),
        plan_type=p.plan_type,
        status=p.status,
        due_date=p.due_date,
        notes=p.notes,
        created_at=p.created_at,
        updated_at=p.updated_at,
        assigned_to=_map_user(p.assigned_to) if p.assigned_to else None,
    )


def _map_entry(e) -> SERSEntryType:
    return SERSEntryType(
        id=strawberry.ID(str(e.pk)),
        period_label=e.period_label,
        unexcused_absences=e.unexcused_absences,
        grade_drop_points=e.grade_drop_points,
        disciplinary_flags=e.disciplinary_flags,
        wellbeing_score=e.wellbeing_score,
        notes=e.notes,
        sers_score=e.sers_score,
        risk_level=e.risk_level,
        risk_explanation=e.risk_explanation,
        workflow_state=e.workflow_state,
        created_at=e.created_at,
        updated_at=e.updated_at,
        student=_map_student(e.student),
        operator=_map_user(e.operator),
    )
