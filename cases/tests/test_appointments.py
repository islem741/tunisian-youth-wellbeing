"""Tests for Scenario 2 (follow-up + automatic reminder)."""

from __future__ import annotations

import pytest
from django.utils import timezone
from datetime import timedelta

from cases.models import Appointment, CaseEvent


@pytest.mark.django_db
def test_missing_appointment_triggers_reminder(high_risk_assessment, supervisor):
    appt = Appointment.objects.create(
        assessment=high_risk_assessment,
        scheduled_for=timezone.now() - timedelta(days=1),
        scheduled_by=supervisor,
    )
    assert not high_risk_assessment.events.filter(
        action=CaseEvent.Action.REMINDER
    ).exists()

    appt.mark_missed(actor=supervisor)

    appt.refresh_from_db()
    assert appt.status == Appointment.Status.MISSED
    assert high_risk_assessment.events.filter(
        action=CaseEvent.Action.REMINDER
    ).count() == 1
    assert high_risk_assessment.events.filter(
        action=CaseEvent.Action.APPOINTMENT,
        detail__contains="Missed",
    ).exists()
