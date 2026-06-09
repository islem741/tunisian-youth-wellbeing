"""Signals for the support app.

post_save on MoodScore handles Scenario 1:
  3 consecutive low mood scores → notify peer supporter + auto-escalate
  to counselor by creating a PENDING SupportSession.
"""

from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender="support.MoodScore")
def check_auto_escalation(sender, instance, created, **kwargs):
    if not created:
        return

    # Import here to avoid circular imports at module load time.
    from .models import Assignment, AuditEvent, MoodScore, SupportSession

    youth = instance.youth
    if not MoodScore.check_consecutive_low(youth):
        return

    assignment = Assignment.objects.filter(youth=youth, is_active=True).first()
    if assignment is None:
        return

    # Notify peer supporter via audit log.
    AuditEvent.objects.create(
        actor=None,
        youth=youth,
        action=AuditEvent.Action.AUTO_ESCALATION,
        detail=(
            f"Youth {youth.username} logged 3 consecutive low mood scores. "
            f"Peer supporter {assignment.peer_supporter.username} notified. "
            f"Auto-escalating to counselor."
        ),
    )

    # If a counselor is assigned, open a PENDING session for their review.
    if assignment.counselor:
        SupportSession.objects.create(
            assignment=assignment,
            logged_by=assignment.peer_supporter,
            notes="[AUTO] System generated: 3 consecutive low mood scores detected.",
            escalation_status=SupportSession.EscalationStatus.PENDING,
        )
