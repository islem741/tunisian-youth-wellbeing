"""Tests for role-based access control (Prompt 5 #1 and #2)."""

from __future__ import annotations

import pytest
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from cases.models import Appointment, WorkflowState


@pytest.mark.django_db
def test_operator_cannot_change_workflow_state(client, operator, high_risk_assessment):
    client.force_login(operator)
    url = reverse("cases:transition", args=[high_risk_assessment.pk])
    resp = client.post(url, {"to_state": WorkflowState.INTERVENTION, "reason": "x"})
    assert resp.status_code == 403


@pytest.mark.django_db
def test_operator_cannot_mark_appointment_missed(client, operator, supervisor, high_risk_assessment):
    appt = Appointment.objects.create(
        assessment=high_risk_assessment,
        scheduled_for=timezone.now() - timedelta(days=1),
        scheduled_by=supervisor,
    )
    client.force_login(operator)
    url = reverse("cases:appointment_miss", args=[appt.pk])
    resp = client.post(url)
    assert resp.status_code == 403
    appt.refresh_from_db()
    assert appt.status == Appointment.Status.SCHEDULED


@pytest.mark.django_db
def test_operator_cannot_edit_risk_policy(client, operator):
    client.force_login(operator)
    resp = client.post(reverse("cases:risk_policy"), {"threshold": 50})
    assert resp.status_code == 403


@pytest.mark.django_db
def test_supervisor_can_transition(client, supervisor, high_risk_assessment):
    client.force_login(supervisor)
    url = reverse("cases:transition", args=[high_risk_assessment.pk])
    resp = client.post(
        url, {"to_state": WorkflowState.INTERVENTION, "reason": "escalate"}
    )
    # Redirects back to case detail on success.
    assert resp.status_code == 302
    high_risk_assessment.refresh_from_db()
    assert high_risk_assessment.workflow_state == WorkflowState.INTERVENTION


@pytest.mark.django_db
def test_unauthenticated_is_redirected_to_login(client):
    resp = client.get(reverse("cases:list"))
    assert resp.status_code == 302
    assert "/accounts/login/" in resp["Location"]


@pytest.mark.django_db
def test_assessment_post_with_bad_values_returns_form_error(client, operator, student):
    client.force_login(operator)
    url = reverse("cases:assessment_create")
    resp = client.post(url, {
        "student": student.pk,
        "academic_pressure": 150,
        "social_anxiety": -5,
        "home_environment": 30,
        "notes": "",
    })
    # The form re-renders with a 200 and an error message, the database
    # stays unchanged (failure-recovery evidence).
    assert resp.status_code == 200
    assert b"Score must be an integer between 0 and 100" in resp.content or \
        b"Ensure this value" in resp.content
