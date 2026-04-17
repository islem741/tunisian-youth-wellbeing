"""Tests for the risk engine and workflow state machine (Prompt 5)."""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from cases.models import RiskLevel, StressAssessment, WorkflowState


@pytest.mark.django_db
def test_high_score_is_flagged_high_risk(operator, student, risk_policy):
    """Prompt 5 #3: score exceeding threshold transitions to High Risk."""

    a = StressAssessment.objects.create(
        student=student,
        operator=operator,
        academic_pressure=80,
        social_anxiety=70,
        home_environment=60,
    )
    assert a.total_score == 210
    assert a.risk_level == RiskLevel.HIGH
    # New high-risk cases are automatically moved to "Assessment" so the
    # Supervisor immediately sees them in their queue.
    assert a.workflow_state == WorkflowState.ASSESSMENT
    assert "High-Risk threshold" in a.risk_explanation


@pytest.mark.django_db
def test_low_score_stays_low(operator, student, risk_policy):
    a = StressAssessment.objects.create(
        student=student,
        operator=operator,
        academic_pressure=10,
        social_anxiety=10,
        home_environment=10,
    )
    assert a.risk_level == RiskLevel.LOW
    assert a.workflow_state == WorkflowState.INTAKE


@pytest.mark.django_db
def test_threshold_is_configurable(operator, student, risk_policy):
    risk_policy.threshold = 30
    risk_policy.save()
    a = StressAssessment.objects.create(
        student=student,
        operator=operator,
        academic_pressure=10,
        social_anxiety=10,
        home_environment=10,
    )
    assert a.total_score == 30
    assert a.risk_level == RiskLevel.HIGH


@pytest.mark.django_db
def test_impossible_score_is_rejected(operator, student):
    """Prompt 3: impossible values raise a validation error, not a crash."""

    assessment = StressAssessment(
        student=student,
        operator=operator,
        academic_pressure=150,
        social_anxiety=-5,
        home_environment=20,
    )
    with pytest.raises(ValidationError) as excinfo:
        assessment.save()
    errors = excinfo.value.message_dict
    assert "academic_pressure" in errors
    assert "social_anxiety" in errors


@pytest.mark.django_db
def test_illegal_transition_is_rejected(high_risk_assessment, supervisor):
    # High-risk assessments start in ASSESSMENT; going straight to
    # CLOSED is allowed, but jumping directly to FOLLOW_UP must fail.
    with pytest.raises(ValidationError):
        high_risk_assessment.transition_to(
            WorkflowState.FOLLOW_UP, actor=supervisor
        )


@pytest.mark.django_db
def test_legal_transition_logs_event(high_risk_assessment, supervisor):
    event = high_risk_assessment.transition_to(
        WorkflowState.INTERVENTION, actor=supervisor
    )
    high_risk_assessment.refresh_from_db()
    assert high_risk_assessment.workflow_state == WorkflowState.INTERVENTION
    assert event.actor == supervisor
    assert event.from_state == WorkflowState.ASSESSMENT
    assert event.to_state == WorkflowState.INTERVENTION
