import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from accounts.models import Role
from cases.models import (
    CaseEvent, InterventionPlan, SERSEntry, SERSPolicy,
    Student, WorkflowState,
)

User = get_user_model()


@pytest.fixture
def supervisor(db):
    u = User.objects.create_user(
        username="sup_wf", password="pw", role=Role.SUPERVISOR,
    )
    u.sync_groups()
    return u


@pytest.fixture
def entry(db, supervisor):
    SERSPolicy.objects.get_or_create(
        pk=1,
        defaults={"high_threshold": 65, "medium_threshold": 40},
    )
    s = Student.objects.create(
        external_id="STU-WF-001",
        first_name="A", last_name="B",
        age=14, school="Sc", region="Tunis",
    )
    op = User.objects.create_user(
        username="op_wf", password="pw",
        role=Role.OPERATOR, school="Sc",
    )
    op.sync_groups()
    return SERSEntry.objects.create(
        student=s, operator=op,
        unexcused_absences=0, grade_drop_points=0,
        disciplinary_flags=0, wellbeing_score=8,
    )


def test_valid_transition(db, entry, supervisor):
    entry.transition_to(WorkflowState.ASSESSMENT, actor=supervisor)
    entry.refresh_from_db()
    assert entry.workflow_state == WorkflowState.ASSESSMENT


def test_illegal_transition_raises(db, entry, supervisor):
    with pytest.raises(ValidationError):
        entry.transition_to(WorkflowState.FOLLOW_UP, actor=supervisor)


def test_transition_logged_in_audit(db, entry, supervisor):
    entry.transition_to(WorkflowState.ASSESSMENT, actor=supervisor)
    assert CaseEvent.objects.filter(
        entry=entry,
        action=CaseEvent.Action.STATE_CHANGE,
    ).exists()


def test_intervention_plan_created_and_completed(db, entry, supervisor):
    entry.transition_to(WorkflowState.ASSESSMENT, actor=supervisor)
    entry.transition_to(WorkflowState.INTERVENTION, actor=supervisor)
    plan = InterventionPlan.objects.create(
        entry=entry,
        plan_type=InterventionPlan.PlanType.TUTORING,
        assigned_to=supervisor,
    )
    plan.mark_completed(actor=supervisor)
    plan.refresh_from_db()
    assert plan.status == InterventionPlan.PlanStatus.COMPLETED
