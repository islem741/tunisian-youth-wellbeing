"""GraphQL permission classes (Strawberry BasePermission).

Each class maps directly to the existing accounts.models.Role choices:
  - IsAuthenticated      — any logged-in user
  - IsOperatorOrAbove    — operator | supervisor | admin
  - IsSupervisorOrAbove  — supervisor | admin
  - IsAdmin              — admin only

All permission failures return structured GraphQL errors via
PermissionError, which Strawberry converts to the standard
{"errors": [...]} response — never an HTTP 403, because GraphQL
always returns HTTP 200 with errors in the payload.

The check() method receives ``strawberry.Info`` which gives access to
``info.context.request`` (the Django HttpRequest), matching how Django
middleware works in the rest of the project.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import strawberry
from strawberry.permission import BasePermission
from strawberry.types import Info

if TYPE_CHECKING:
    pass  # keep imports clean


def _get_request(info: Info):
    """Return the Django request regardless of whether context is a dict or object."""
    ctx = info.context
    if isinstance(ctx, dict):
        return ctx.get("request")
    return getattr(ctx, "request", None)


class IsAuthenticated(BasePermission):
    """Reject unauthenticated requests."""

    message = "You must be logged in to access this resource."

    def has_permission(self, source, info: Info, **kwargs) -> bool:
        request = _get_request(info)
        if not request:
            return False
        return bool(request.user and request.user.is_authenticated)


class IsOperatorOrAbove(BasePermission):
    """Allow Operator, Supervisor, or Admin. Reject everyone else."""

    message = "You must be an Operator, Supervisor, or Admin."

    def has_permission(self, source, info: Info, **kwargs) -> bool:
        request = _get_request(info)
        if not request or not request.user or not request.user.is_authenticated:
            return False
        return getattr(request.user, "role", None) in (
            "operator", "supervisor", "admin"
        )


class IsSupervisorOrAbove(BasePermission):
    """Allow Supervisor or Admin. Block Operators and unauthenticated users."""

    message = "You must be a Supervisor or Admin to perform this action."

    def has_permission(self, source, info: Info, **kwargs) -> bool:
        request = _get_request(info)
        if not request or not request.user or not request.user.is_authenticated:
            return False
        return getattr(request.user, "role", None) in ("supervisor", "admin")


class IsAdmin(BasePermission):
    """Allow Admin only."""

    message = "You must be an Admin to perform this action."

    def has_permission(self, source, info: Info, **kwargs) -> bool:
        request = _get_request(info)
        if not request or not request.user or not request.user.is_authenticated:
            return False
        return getattr(request.user, "role", None) == "admin"
