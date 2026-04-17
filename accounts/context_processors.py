"""Template context helpers so templates can gate blocks by role."""

from __future__ import annotations


def role_flags(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {
            "is_operator": False,
            "is_supervisor": False,
            "is_program_admin": False,
        }
    return {
        "is_operator": getattr(user, "is_operator", False),
        "is_supervisor": getattr(user, "is_supervisor", False),
        "is_program_admin": getattr(user, "is_program_admin", False),
    }
