"""Support-app permission helpers.

assert_supporter_owns_youth — Scenario 2 guard.
Raises PermissionDenied (and writes two AuditEvents) when a Peer Supporter
tries to access a Youth they are not assigned to.
Counselors and Supervisors are always allowed through.
"""

from __future__ import annotations


def assert_supporter_owns_youth(request_user, youth_pk: int) -> None:
    """Raise PermissionDenied if ``request_user`` is a Peer Supporter
    who is NOT assigned to ``youth_pk``.

    Also logs an ACCESS_DENIED and a SUPERVISOR_ALERT audit event so
    the attempt is visible in the audit trail.
    """
    from django.core.exceptions import PermissionDenied

    from accounts.models import Role

    from .models import Assignment, AuditEvent

    if request_user.role != Role.PEER_SUPPORTER:
        return  # supervisors and admins may view all

    assigned = Assignment.objects.filter(
        peer_supporter=request_user,
        youth_id=youth_pk,
        is_active=True,
    ).exists()

    if not assigned:
        AuditEvent.objects.create(
            actor=request_user,
            youth_id=youth_pk,
            action=AuditEvent.Action.ACCESS_DENIED,
            detail=(
                f"Peer supporter {request_user.username} attempted to access "
                f"youth #{youth_pk} (not assigned)."
            ),
        )
        AuditEvent.objects.create(
            actor=None,
            youth_id=youth_pk,
            action=AuditEvent.Action.SUPERVISOR_ALERT,
            detail=(
                f"ALERT: Unauthorized access attempt by {request_user.username} "
                f"on youth #{youth_pk}. Supervisor notified."
            ),
        )
        raise PermissionDenied(
            "You are not assigned to this youth. "
            "This attempt has been logged."
        )
