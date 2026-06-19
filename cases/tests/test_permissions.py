import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from accounts.models import Role
from cases.models import CaseEvent, SERSEntry, SERSPolicy, Student

User = get_user_model()


@pytest.fixture
def supervisor(db):
    u = User.objects.create_user(
        username="sup_perm", password="pw", role=Role.SUPERVISOR,
    )
    u.sync_groups()
    return u


@pytest.fixture
def operator(db):
    u = User.objects.create_user(
        username="op_perm", password="pw",
        role=Role.OPERATOR, school="School A",
    )
    u.sync_groups()
    return u


@pytest.fixture
def other_operator(db):
    u = User.objects.create_user(
        username="op_other", password="pw",
        role=Role.OPERATOR, school="School B",
    )
    u.sync_groups()
    return u


@pytest.fixture
def policy(db):
    p, _ = SERSPolicy.objects.get_or_create(
        pk=1,
        defaults={"high_threshold": 65, "medium_threshold": 40},
    )
    return p


@pytest.fixture
def entry(db, operator, policy):
    s = Student.objects.create(
        external_id="STU-PERM-001",
        first_name="A", last_name="B",
        age=14, school="School A", region="Tunis",
    )
    return SERSEntry.objects.create(
        student=s, operator=operator,
        unexcused_absences=0, grade_drop_points=0,
        disciplinary_flags=0, wellbeing_score=8,
    )


def test_operator_cannot_access_other_school_case(db, other_operator, entry, client):
    client.force_login(other_operator)
    response = client.get(reverse("cases:detail", args=[entry.pk]))
    assert response.status_code == 403


def test_security_event_logged_on_unauthorized_access(db, other_operator, entry, client):
    client.force_login(other_operator)
    client.get(reverse("cases:detail", args=[entry.pk]))
    assert CaseEvent.objects.filter(
        action=CaseEvent.Action.SECURITY, entry=entry,
    ).exists()


def test_operator_cannot_view_sers_policy(db, operator, client):
    client.force_login(operator)
    response = client.get(reverse("cases:sers_policy"))
    assert response.status_code == 403


def test_supervisor_cannot_create_entry(db, supervisor, client):
    client.force_login(supervisor)
    response = client.get(reverse("cases:entry_create"))
    assert response.status_code == 403


def test_supervisor_can_view_case(db, supervisor, entry, client):
    client.force_login(supervisor)
    response = client.get(reverse("cases:detail", args=[entry.pk]))
    assert response.status_code == 200
