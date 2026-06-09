import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from accounts.models import Role
from cases.models import RiskLevel, SERSEntry, SERSPolicy, Student, WorkflowState

User = get_user_model()


@pytest.fixture
def policy(db):
    p, _ = SERSPolicy.objects.get_or_create(
        pk=1,
        defaults={
            "absence_weight": 6, "grade_drop_weight": 5,
            "behavior_weight": 8, "wellbeing_weight": 10,
            "high_threshold": 65, "medium_threshold": 40,
        },
    )
    return p


@pytest.fixture
def op(db):
    u = User.objects.create_user(
        username="op_test", password="pw",
        role=Role.OPERATOR, school="Test School",
    )
    u.sync_groups()
    return u


@pytest.fixture
def student(db):
    return Student.objects.create(
        external_id="STU-TEST-001",
        first_name="Amira", last_name="Test",
        age=15, school="Test School", region="Tunis",
    )


def test_sers_formula(db, op, student, policy):
    """compute_sers uses weights correctly."""
    entry = SERSEntry(
        student=student, operator=op,
        unexcused_absences=3, grade_drop_points=4,
        disciplinary_flags=1, wellbeing_score=3,
    )
    score, explanation = entry.compute_sers(policy)
    # 3*6 + 4*5 + 1*8 + (10-3)*10 = 18+20+8+70 = 116 → capped at 100
    assert score == 100
    assert "Absences" in explanation


def test_high_risk_classification(db, op, student, policy):
    entry = SERSEntry.objects.create(
        student=student, operator=op,
        unexcused_absences=5, grade_drop_points=5,
        disciplinary_flags=2, wellbeing_score=2,
    )
    assert entry.risk_level == RiskLevel.HIGH


def test_low_risk_classification(db, op, student, policy):
    entry = SERSEntry.objects.create(
        student=student, operator=op,
        unexcused_absences=0, grade_drop_points=0,
        disciplinary_flags=0, wellbeing_score=9,
    )
    assert entry.risk_level == RiskLevel.LOW


def test_invalid_wellbeing_rejected(db, op, student, policy):
    with pytest.raises(ValidationError):
        SERSEntry.objects.create(
            student=student, operator=op,
            unexcused_absences=0, grade_drop_points=0,
            disciplinary_flags=0, wellbeing_score=11,  # invalid
        )


def test_high_risk_auto_promoted_to_assessment(db, op, student, policy):
    entry = SERSEntry.objects.create(
        student=student, operator=op,
        unexcused_absences=8, grade_drop_points=8,
        disciplinary_flags=3, wellbeing_score=1,
    )
    assert entry.workflow_state == WorkflowState.ASSESSMENT
