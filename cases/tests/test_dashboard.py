"""Dashboard view tests.

Covers:
1. Admin KPI page returns 200 and expected content.
2. Operator is forbidden from the Admin KPI page.
3. Supervisor queue shows ASSESSMENT/INTERVENTION cases only —
   a low-risk INTAKE entry must NOT appear.
4. completion_rate context variable is computed correctly when
   at least one entry has been closed.
5. Export CSV returns correct content-type and the expected header row.
"""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.models import Role
from cases.models import SERSEntry, SERSPolicy, Student, WorkflowState

User = get_user_model()


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

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
def admin_user(db):
    u = User.objects.create_user(
        username="dash_admin", password="pw",
        role=Role.ADMIN, is_staff=True,
    )
    u.sync_groups()
    return u


@pytest.fixture
def supervisor_user(db):
    u = User.objects.create_user(
        username="dash_sup", password="pw", role=Role.SUPERVISOR,
    )
    u.sync_groups()
    return u


@pytest.fixture
def operator_user(db):
    u = User.objects.create_user(
        username="dash_op", password="pw",
        role=Role.OPERATOR, school="Test School",
    )
    u.sync_groups()
    return u


@pytest.fixture
def base_student(db):
    return Student.objects.create(
        external_id="STU-DASH-001",
        first_name="Test", last_name="Student",
        age=15, school="Test School", region="Tunis",
    )


def make_entry(student, operator, policy, *, high=False):
    """Create a HIGH-risk or LOW-risk SERSEntry."""
    if high:
        return SERSEntry.objects.create(
            student=student, operator=operator,
            unexcused_absences=8, grade_drop_points=8,
            disciplinary_flags=3, wellbeing_score=1,
        )
    return SERSEntry.objects.create(
        student=student, operator=operator,
        unexcused_absences=0, grade_drop_points=0,
        disciplinary_flags=0, wellbeing_score=9,
    )


# ---------------------------------------------------------------------------
# 1. Admin KPI page — 200 for Admin
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_admin_kpis_returns_200_for_admin(client, admin_user, policy):
    client.force_login(admin_user)
    response = client.get(reverse("dashboard:admin_kpis"))
    assert response.status_code == 200
    # Template renders the "Workflow Completion" label
    assert b"Workflow Completion" in response.content


# ---------------------------------------------------------------------------
# 2. Admin KPI page — 403 for Operator
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_admin_kpis_forbidden_for_operator(client, operator_user):
    client.force_login(operator_user)
    response = client.get(reverse("dashboard:admin_kpis"))
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# 3. Supervisor queue — shows only ASSESSMENT/INTERVENTION cases
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_supervisor_queue_shows_only_active_cases(
    client, supervisor_user, operator_user, base_student, policy
):
    high_entry = make_entry(base_student, operator_user, policy, high=True)
    # HIGH-risk entry is auto-promoted to ASSESSMENT on save
    assert high_entry.workflow_state == WorkflowState.ASSESSMENT

    # Create a second student for the low-risk entry
    low_student = Student.objects.create(
        external_id="STU-DASH-002",
        first_name="Low", last_name="Risk",
        age=14, school="Test School", region="Tunis",
    )
    low_entry = make_entry(low_student, operator_user, policy, high=False)
    # LOW-risk entry stays in INTAKE
    assert low_entry.workflow_state == WorkflowState.INTAKE

    client.force_login(supervisor_user)
    response = client.get(reverse("dashboard:supervisor_queue"))
    assert response.status_code == 200

    # Assert via the context queryset — not raw HTML, which may contain
    # numeric pk values in unrelated links or pagination elements.
    entry_pks = {e.pk for e in response.context["entries"]}
    assert high_entry.pk in entry_pks
    assert low_entry.pk not in entry_pks


# ---------------------------------------------------------------------------
# 4. completion_rate is > 0 after closing an entry
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_kpi_completion_rate_computed(
    client, admin_user, supervisor_user, operator_user, base_student, policy
):
    # Create one entry and close it via the state machine
    entry = make_entry(base_student, operator_user, policy, high=False)
    # Move INTAKE → ASSESSMENT → CLOSED
    entry.transition_to(WorkflowState.ASSESSMENT, actor=supervisor_user)
    entry.transition_to(WorkflowState.CLOSED,     actor=supervisor_user)
    entry.refresh_from_db()
    assert entry.workflow_state == WorkflowState.CLOSED

    client.force_login(admin_user)
    response = client.get(reverse("dashboard:admin_kpis"))
    assert response.status_code == 200
    # completion_rate = closed/total * 100 — must be > 0
    assert response.context["completion_rate"] > 0


# ---------------------------------------------------------------------------
# 5. CSV export — content-type and header row
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_export_csv_returns_csv_content_type(
    client, supervisor_user, operator_user, base_student, policy
):
    # Need at least one entry so the export is non-trivial
    make_entry(base_student, operator_user, policy, high=False)

    client.force_login(supervisor_user)
    response = client.get(reverse("cases:export_csv"))
    assert response.status_code == 200
    assert "text/csv" in response["Content-Type"]

    # First line must be the header row
    first_line = response.content.decode().splitlines()[0]
    assert "sers_score" in first_line
    assert "student_name" in first_line
    assert "risk_level"   in first_line
