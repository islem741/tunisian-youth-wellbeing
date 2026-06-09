"""Automated tests for the GraphQL API.

Coverage:
  Successful queries (7):
    test_me_query_returns_current_user
    test_students_query_scoped_to_operator_school
    test_sers_entries_query_returns_list
    test_sers_entry_filter_by_risk_level
    test_case_events_query_returns_audit_trail
    test_sers_policy_query
    test_dashboard_metrics_admin_only

  Successful mutations (6):
    test_create_student_mutation
    test_create_sers_entry_mutation
    test_transition_case_mutation
    test_create_intervention_plan_mutation
    test_complete_intervention_plan_mutation
    test_update_sers_policy_mutation

  Permission failures (6):
    test_unauthenticated_request_returns_error
    test_operator_cannot_access_dashboard_metrics
    test_operator_cannot_update_sers_policy
    test_operator_cannot_transition_case
    test_operator_cannot_create_intervention_plan
    test_operator_scoped_cannot_see_other_school_entry

  Validation failures (4):
    test_create_student_duplicate_external_id
    test_create_sers_entry_invalid_wellbeing_score
    test_create_student_invalid_gender
    test_transition_invalid_state
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Optional

import pytest

from accounts.models import Role
from cases.models import (
    CaseEvent, InterventionPlan, SERSEntry, SERSPolicy, Student, WorkflowState,
)
from gql.schema import schema


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeRequest:
    """Minimal fake Django request for Strawberry context."""
    def __init__(self, user):
        self.user = user


@dataclass
class _Result:
    data:   Optional[Dict[str, Any]]
    errors: Optional[list]


def _exec(user, query: str, variables: Optional[dict] = None) -> _Result:
    """Execute a GraphQL query/mutation synchronously with a fake request."""
    result = schema.execute_sync(
        query,
        variable_values=variables,
        context_value={"request": _FakeRequest(user)},
    )
    return _Result(data=result.data, errors=result.errors)


class _AnonymousUser:
    is_authenticated = False
    role = None


def _anon_exec(query: str, variables: Optional[dict] = None) -> _Result:
    return _exec(_AnonymousUser(), query, variables)


# ---------------------------------------------------------------------------
# Fixtures
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
def op_user(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    u = User.objects.create_user(
        username="gql_op", password="pw",
        role=Role.OPERATOR, school="School A", region="Tunis",
    )
    u.sync_groups()
    return u


@pytest.fixture
def op_user_b(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    u = User.objects.create_user(
        username="gql_op_b", password="pw",
        role=Role.OPERATOR, school="School B", region="Ariana",
    )
    u.sync_groups()
    return u


@pytest.fixture
def sup_user(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    u = User.objects.create_user(
        username="gql_sup", password="pw", role=Role.SUPERVISOR,
    )
    u.sync_groups()
    return u


@pytest.fixture
def admin_user(db):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    u = User.objects.create_user(
        username="gql_adm", password="pw", role=Role.ADMIN, is_staff=True,
    )
    u.sync_groups()
    return u


@pytest.fixture
def student_a(db):
    return Student.objects.create(
        external_id="GQL-STU-001",
        first_name="Amira", last_name="Test",
        age=15, school="School A", region="Tunis",
    )


@pytest.fixture
def student_b(db):
    return Student.objects.create(
        external_id="GQL-STU-002",
        first_name="Zied", last_name="Other",
        age=16, school="School B", region="Ariana",
    )


@pytest.fixture
def low_entry(db, op_user, student_a, policy):
    return SERSEntry.objects.create(
        student=student_a, operator=op_user,
        unexcused_absences=0, grade_drop_points=0,
        disciplinary_flags=0, wellbeing_score=9,
    )


@pytest.fixture
def high_entry(db, op_user, student_a, policy):
    return SERSEntry.objects.create(
        student=student_a, operator=op_user,
        unexcused_absences=8, grade_drop_points=8,
        disciplinary_flags=3, wellbeing_score=1,
    )


# ============================================================================
# SUCCESSFUL QUERIES
# ============================================================================

@pytest.mark.django_db
def test_me_query_returns_current_user(op_user):
    """Query 'me' returns the authenticated user's username and role."""
    result = _exec(op_user, "{ me { username role school } }")
    assert result.errors is None
    data = result.data["me"]
    assert data["username"] == "gql_op"
    assert data["role"] == "operator"
    assert data["school"] == "School A"


@pytest.mark.django_db
def test_students_query_scoped_to_operator_school(op_user, student_a, student_b):
    """Operator only sees students from their own school."""
    result = _exec(op_user, "{ students { externalId school } }")
    assert result.errors is None
    ids = [s["externalId"] for s in result.data["students"]]
    assert "GQL-STU-001" in ids          # School A — operator's school
    assert "GQL-STU-002" not in ids      # School B — out of scope


@pytest.mark.django_db
def test_sers_entries_query_returns_list(op_user, low_entry):
    """sersEntries returns at least one entry for the operator."""
    result = _exec(op_user, "{ sersEntries { id sersScore riskLevel workflowState } }")
    assert result.errors is None
    assert len(result.data["sersEntries"]) >= 1
    entry = result.data["sersEntries"][0]
    assert "sersScore" in entry
    assert entry["riskLevel"] in ("low", "medium", "high")


@pytest.mark.django_db
def test_sers_entry_filter_by_risk_level(op_user, low_entry, high_entry):
    """Filtering by riskLevel=high returns only HIGH entries."""
    result = _exec(op_user, '{ sersEntries(filter: { riskLevel: "high" }) { id riskLevel } }')
    assert result.errors is None
    entries = result.data["sersEntries"]
    assert all(e["riskLevel"] == "high" for e in entries)
    assert str(high_entry.pk) in [e["id"] for e in entries]


@pytest.mark.django_db
def test_case_events_query_returns_audit_trail(op_user, low_entry):
    """caseEvents returns the audit log for an entry the operator can access."""
    CaseEvent.objects.create(
        entry=low_entry, actor=op_user,
        action=CaseEvent.Action.INTAKE,
        to_state=low_entry.workflow_state,
        detail="Test event.",
    )
    result = _exec(op_user, f'{{ caseEvents(entryId: "{low_entry.pk}") {{ action detail }} }}')
    assert result.errors is None
    events = result.data["caseEvents"]
    assert len(events) >= 1
    assert any(e["action"] == "intake" for e in events)


@pytest.mark.django_db
def test_sers_policy_query(op_user, policy):
    """sersPolicy returns the singleton policy row."""
    result = _exec(op_user, "{ sersPolicy { highThreshold mediumThreshold absenceWeight } }")
    assert result.errors is None
    p = result.data["sersPolicy"]
    assert p["highThreshold"] == 65
    assert p["mediumThreshold"] == 40
    assert p["absenceWeight"] == 6


@pytest.mark.django_db
def test_dashboard_metrics_admin_only(admin_user, policy, low_entry):
    """dashboardMetrics succeeds for Admin and returns expected fields."""
    result = _exec(
        admin_user,
        "{ dashboardMetrics { totalEntries completionRate securityEventCount } }",
    )
    assert result.errors is None
    m = result.data["dashboardMetrics"]
    assert m["totalEntries"] >= 1
    assert 0.0 <= m["completionRate"] <= 100.0


# ============================================================================
# SUCCESSFUL MUTATIONS
# ============================================================================

@pytest.mark.django_db
def test_create_student_mutation(op_user):
    """createStudent creates a new Student record."""
    mutation = """
        mutation {
          createStudent(data: {
            externalId: "GQL-NEW-001"
            firstName: "Nour"
            lastName: "Gharbi"
            age: 14
            gender: "F"
            school: "Lycee Test"
            region: "Tunis"
          }) {
            ... on StudentType { externalId firstName school }
            ... on MutationError { message field }
          }
        }
    """
    result = _exec(op_user, mutation)
    assert result.errors is None
    payload = result.data["createStudent"]
    assert "externalId" in payload
    assert payload["externalId"] == "GQL-NEW-001"
    assert payload["firstName"] == "Nour"
    assert Student.objects.filter(external_id="GQL-NEW-001").exists()


@pytest.mark.django_db
def test_create_sers_entry_mutation(op_user, student_a, policy):
    """createSersEntry computes score and creates an entry + audit event."""
    mutation = """
        mutation {
          createSersEntry(data: {
            studentExternalId: "GQL-STU-001"
            unexcusedAbsences: 5
            gradeDropPoints: 3
            disciplinaryFlags: 1
            wellbeingScore: 4
            periodLabel: "Test period"
          }) {
            ... on SERSEntryType { id sersScore riskLevel workflowState }
            ... on MutationError { message }
          }
        }
    """
    result = _exec(op_user, mutation)
    assert result.errors is None
    payload = result.data["createSersEntry"]
    assert "sersScore" in payload
    assert payload["sersScore"] > 0
    assert payload["riskLevel"] in ("low", "medium", "high")
    entry_id = int(payload["id"])
    assert CaseEvent.objects.filter(
        entry_id=entry_id, action=CaseEvent.Action.INTAKE
    ).exists()


@pytest.mark.django_db
def test_transition_case_mutation(sup_user, high_entry, policy):
    """Supervisor can transition a HIGH-risk case from assessment to intervention."""
    assert high_entry.workflow_state == WorkflowState.ASSESSMENT
    mutation = f"""
        mutation {{
          transitionCase(data: {{
            entryId: "{high_entry.pk}"
            toState: "intervention"
            reason: "GraphQL transition test."
          }}) {{
            ... on SERSEntryType {{ id workflowState }}
            ... on MutationError {{ message }}
          }}
        }}
    """
    result = _exec(sup_user, mutation)
    assert result.errors is None
    payload = result.data["transitionCase"]
    assert "workflowState" in payload
    assert payload["workflowState"] == "intervention"
    high_entry.refresh_from_db()
    assert high_entry.workflow_state == WorkflowState.INTERVENTION


@pytest.mark.django_db
def test_create_intervention_plan_mutation(sup_user, high_entry, policy):
    """Supervisor can create an intervention plan on a SERS entry."""
    mutation = f"""
        mutation {{
          createInterventionPlan(data: {{
            entryId: "{high_entry.pk}"
            planType: "counseling"
            assignedToId: "{sup_user.pk}"
            dueDate: "2026-09-01"
            notes: "Initial counseling session."
          }}) {{
            ... on InterventionPlanType {{ id planType status }}
            ... on MutationError {{ message }}
          }}
        }}
    """
    result = _exec(sup_user, mutation)
    assert result.errors is None
    payload = result.data["createInterventionPlan"]
    assert "planType" in payload
    assert payload["planType"] == "counseling"
    assert payload["status"] == "pending"
    assert InterventionPlan.objects.filter(entry=high_entry).exists()


@pytest.mark.django_db
def test_complete_intervention_plan_mutation(sup_user, high_entry, policy):
    """Supervisor can mark an intervention plan as completed."""
    plan = InterventionPlan.objects.create(
        entry=high_entry,
        plan_type=InterventionPlan.PlanType.TUTORING,
        assigned_to=sup_user,
        due_date=date(2026, 9, 1),
    )
    mutation = f"""
        mutation {{
          completeInterventionPlan(data: {{ planId: "{plan.pk}" }}) {{
            ... on InterventionPlanType {{ id status }}
            ... on MutationError {{ message }}
          }}
        }}
    """
    result = _exec(sup_user, mutation)
    assert result.errors is None
    payload = result.data["completeInterventionPlan"]
    assert payload["status"] == "completed"
    plan.refresh_from_db()
    assert plan.status == InterventionPlan.PlanStatus.COMPLETED


@pytest.mark.django_db
def test_update_sers_policy_mutation(admin_user, policy):
    """Admin can update the SERS policy weights."""
    mutation = """
        mutation {
          updateSersPolicy(data: {
            absenceWeight: 7
            highThreshold: 70
          }) {
            ... on SERSPolicyType { absenceWeight highThreshold mediumThreshold }
            ... on MutationError { message }
          }
        }
    """
    result = _exec(admin_user, mutation)
    assert result.errors is None
    payload = result.data["updateSersPolicy"]
    assert payload["absenceWeight"] == 7
    assert payload["highThreshold"] == 70
    policy.refresh_from_db()
    assert policy.absence_weight == 7
    assert policy.high_threshold == 70


# ============================================================================
# PERMISSION FAILURES
# ============================================================================

@pytest.mark.django_db
def test_unauthenticated_request_returns_error():
    """Unauthenticated users get a structured permission error."""
    result = _anon_exec("{ me { username } }")
    assert result.errors is not None
    # The me query uses IsOperatorOrAbove; the error message reflects that role requirement
    assert any(
        "Operator" in str(e) or "logged" in str(e) or "permission" in str(e).lower()
        for e in result.errors
    )


@pytest.mark.django_db
def test_operator_cannot_access_dashboard_metrics(op_user, policy):
    """Operators are blocked from dashboardMetrics — Admin only."""
    result = _exec(op_user, "{ dashboardMetrics { totalEntries } }")
    assert result.errors is not None
    assert any("Admin" in str(e) for e in result.errors)


@pytest.mark.django_db
def test_operator_cannot_update_sers_policy(op_user, policy):
    """Operators cannot update the SERS policy."""
    mutation = """
        mutation {
          updateSersPolicy(data: { absenceWeight: 99 }) {
            ... on SERSPolicyType { absenceWeight }
            ... on MutationError { message }
          }
        }
    """
    result = _exec(op_user, mutation)
    assert result.errors is not None
    assert any("Admin" in str(e) for e in result.errors)


@pytest.mark.django_db
def test_operator_cannot_transition_case(op_user, high_entry, policy):
    """Operators cannot call transitionCase — Supervisor/Admin only."""
    mutation = f"""
        mutation {{
          transitionCase(data: {{
            entryId: "{high_entry.pk}"
            toState: "closed"
          }}) {{
            ... on SERSEntryType {{ workflowState }}
            ... on MutationError {{ message }}
          }}
        }}
    """
    result = _exec(op_user, mutation)
    assert result.errors is not None
    assert any("Supervisor" in str(e) for e in result.errors)


@pytest.mark.django_db
def test_operator_cannot_create_intervention_plan(op_user, high_entry, policy):
    """Operators cannot create intervention plans."""
    mutation = f"""
        mutation {{
          createInterventionPlan(data: {{
            entryId: "{high_entry.pk}"
            planType: "counseling"
            assignedToId: "{op_user.pk}"
            dueDate: "2026-09-01"
          }}) {{
            ... on InterventionPlanType {{ id }}
            ... on MutationError {{ message }}
          }}
        }}
    """
    result = _exec(op_user, mutation)
    assert result.errors is not None
    assert any("Supervisor" in str(e) for e in result.errors)


@pytest.mark.django_db
def test_operator_scoped_cannot_see_other_school_entry(op_user_b, low_entry):
    """Operator from School B gets an empty list when querying School A entries."""
    result = _exec(op_user_b, "{ sersEntries { id student { school } } }")
    assert result.errors is None
    entries = result.data["sersEntries"]
    school_a_ids = [e["id"] for e in entries if e["student"]["school"] == "School A"]
    assert school_a_ids == []


# ============================================================================
# VALIDATION FAILURES
# ============================================================================

@pytest.mark.django_db
def test_create_student_duplicate_external_id(op_user, student_a):
    """Creating a student with an existing external_id returns a MutationError."""
    mutation = """
        mutation {
          createStudent(data: {
            externalId: "GQL-STU-001"
            firstName: "Duplicate"
            lastName: "Student"
            age: 15
            gender: "M"
          }) {
            ... on StudentType { externalId }
            ... on MutationError { message field }
          }
        }
    """
    result = _exec(op_user, mutation)
    assert result.errors is None
    payload = result.data["createStudent"]
    assert "message" in payload          # is a MutationError
    assert "already exists" in payload["message"]
    assert payload["field"] == "external_id"


@pytest.mark.django_db
def test_create_sers_entry_invalid_wellbeing_score(op_user, student_a, policy):
    """wellbeing_score=11 is out of range — MutationError, nothing persisted."""
    mutation = """
        mutation {
          createSersEntry(data: {
            studentExternalId: "GQL-STU-001"
            wellbeingScore: 11
          }) {
            ... on SERSEntryType { id sersScore }
            ... on MutationError { message }
          }
        }
    """
    result = _exec(op_user, mutation)
    assert result.errors is None
    payload = result.data["createSersEntry"]
    assert "message" in payload
    assert not SERSEntry.objects.filter(wellbeing_score=11).exists()


@pytest.mark.django_db
def test_create_student_invalid_gender(op_user):
    """Gender value outside F/M/O returns a MutationError."""
    mutation = """
        mutation {
          createStudent(data: {
            externalId: "GQL-BAD-GENDER"
            firstName: "X"
            lastName: "Y"
            age: 15
            gender: "Z"
          }) {
            ... on StudentType { externalId }
            ... on MutationError { message field }
          }
        }
    """
    result = _exec(op_user, mutation)
    assert result.errors is None
    payload = result.data["createStudent"]
    assert "message" in payload
    assert payload["field"] == "gender"


@pytest.mark.django_db
def test_transition_invalid_state(sup_user, low_entry, policy):
    """Transitioning from INTAKE directly to intervention is an illegal transition."""
    mutation = f"""
        mutation {{
          transitionCase(data: {{
            entryId: "{low_entry.pk}"
            toState: "intervention"
          }}) {{
            ... on SERSEntryType {{ workflowState }}
            ... on MutationError {{ message }}
          }}
        }}
    """
    result = _exec(sup_user, mutation)
    assert result.errors is None
    payload = result.data["transitionCase"]
    assert "message" in payload
    assert "Illegal transition" in payload["message"]
