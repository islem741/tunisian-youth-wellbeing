"""Read-only DRF views for the cases API.

All endpoints require the user to be logged in (SessionAuthentication).
A custom permission class (IsOperatorOrAbove) rejects anonymous users
and any role that does not belong to the platform.

Scoping mirrors the HTML views:
  - Operators  → own submissions + their school's entries
  - Supervisors / Admins → all entries
"""

from __future__ import annotations

from rest_framework import generics
from rest_framework.authentication import SessionAuthentication
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission, IsAuthenticated

from cases.models import CaseEvent, SERSEntry
from cases.api.serializers import CaseEventSerializer, SERSEntrySerializer


# ---------------------------------------------------------------------------
# Custom permission
# ---------------------------------------------------------------------------

class IsOperatorOrAbove(BasePermission):
    """Allow any authenticated user who has a platform role.

    Returns HTTP 403 (not 401) for authenticated users who lack a role,
    and redirects unauthenticated users via the standard 403 response
    consistent with the rest of the project.
    """

    message = "You must be an Operator, Supervisor, or Admin to access the API."

    def has_permission(self, request, view) -> bool:
        if not request.user or not request.user.is_authenticated:
            return False
        role = getattr(request.user, "role", None)
        return role in ("operator", "supervisor", "admin")


# ---------------------------------------------------------------------------
# Scoping helper (mirrors cases/views._scoped_entries)
# ---------------------------------------------------------------------------

def _scoped_entries(user):
    qs = SERSEntry.objects.select_related("student", "operator")
    if user.is_program_admin or user.is_supervisor:
        return qs.order_by("-created_at")
    if user.is_operator:
        base = qs.filter(operator=user)
        if user.school:
            base = (base | qs.filter(student__school=user.school)).distinct()
        return base.order_by("-created_at")
    return qs.none()


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

class SERSEntryListView(generics.ListAPIView):
    """GET /api/cases/
    Returns SERS entries scoped to the caller's role.
    Optional query params: ?risk_level=high|medium|low
                           ?workflow_state=intake|assessment|intervention|follow_up|closed
    """
    serializer_class    = SERSEntrySerializer
    authentication_classes = [SessionAuthentication]
    permission_classes  = [IsAuthenticated, IsOperatorOrAbove]

    def get_queryset(self):
        qs = _scoped_entries(self.request.user)
        risk = self.request.query_params.get("risk_level")
        state = self.request.query_params.get("workflow_state")
        if risk:
            qs = qs.filter(risk_level=risk)
        if state:
            qs = qs.filter(workflow_state=state)
        return qs


class SERSEntryDetailView(generics.RetrieveAPIView):
    """GET /api/cases/{id}/
    Returns a single SERS entry (same scoping as the list view).
    """
    serializer_class    = SERSEntrySerializer
    authentication_classes = [SessionAuthentication]
    permission_classes  = [IsAuthenticated, IsOperatorOrAbove]

    def get_queryset(self):
        return _scoped_entries(self.request.user)


class CaseEventListView(generics.ListAPIView):
    """GET /api/cases/{id}/events/
    Returns the audit trail for a single SERS entry.
    Scoping: same rules as SERSEntryDetailView — Operators can only see
    events for cases they are allowed to access.
    """
    serializer_class    = CaseEventSerializer
    authentication_classes = [SessionAuthentication]
    permission_classes  = [IsAuthenticated, IsOperatorOrAbove]

    def get_queryset(self):
        entry_pk = self.kwargs["pk"]
        # Verify the caller can access this entry at all.
        entry_qs = _scoped_entries(self.request.user).filter(pk=entry_pk)
        if not entry_qs.exists():
            raise PermissionDenied("You do not have access to this case.")
        return (
            CaseEvent.objects.filter(entry_id=entry_pk)
            .select_related("actor")
            .order_by("-created_at")
        )
