"""Tests for the monitoring dashboard (Prompt 4)."""

from __future__ import annotations

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_admin_kpis_visible_to_admin(client, program_admin, high_risk_assessment):
    client.force_login(program_admin)
    resp = client.get(reverse("dashboard:admin_kpis"))
    assert resp.status_code == 200
    assert b"Workflow completion rate" in resp.content
    assert b"Data validation pass rate" in resp.content


@pytest.mark.django_db
def test_admin_kpis_forbidden_to_operator(client, operator):
    client.force_login(operator)
    resp = client.get(reverse("dashboard:admin_kpis"))
    assert resp.status_code == 403


@pytest.mark.django_db
def test_supervisor_queue_only_shows_active_cases(
    client, supervisor, high_risk_assessment, low_risk_assessment
):
    client.force_login(supervisor)
    resp = client.get(reverse("dashboard:supervisor_queue"))
    assert resp.status_code == 200
    body = resp.content.decode()
    assert str(high_risk_assessment.pk) in body
    # Low-risk case is still in "Intake" so it must NOT appear on
    # the supervisor queue.
    assert f">{low_risk_assessment.pk}<" not in body
