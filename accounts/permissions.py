"""Reusable role-based access-control helpers.

Rather than sprinkling ``if user.role == ...`` checks across the
codebase we expose thin decorators and mixins here. They return a
``403 Forbidden`` (as required by the test suite and Track B evidence)
when an authenticated user tries to access a resource outside their
role. Anonymous users are redirected to the login page as usual.
"""

from __future__ import annotations

from functools import wraps
from typing import Callable, Iterable

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse

from .models import Role


def role_required(*roles: str) -> Callable:
    allowed: set[str] = {Role(r).value for r in roles}

    def decorator(view_func: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
        @wraps(view_func)
        @login_required
        def _wrapped(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            user = request.user
            if getattr(user, "role", None) not in allowed:
                raise PermissionDenied(
                    f"Role '{getattr(user, 'role', 'anonymous')}' is not allowed here."
                )
            return view_func(request, *args, **kwargs)

        return _wrapped

    return decorator


class RoleRequiredMixin:
    """Class-based view mixin requiring the user to have one of ``roles``."""

    roles: Iterable[str] = ()

    def dispatch(self, request, *args, **kwargs):  # type: ignore[override]
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login

            return redirect_to_login(request.get_full_path())
        allowed = {Role(r).value for r in self.roles}
        if request.user.role not in allowed:
            raise PermissionDenied(
                f"Role '{request.user.role}' is not allowed to access this page."
            )
        return super().dispatch(request, *args, **kwargs)  # type: ignore[misc]
