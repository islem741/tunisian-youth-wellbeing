"""Custom user model with three mutually-exclusive roles.

The project statement mandates a custom User model with at least the
roles Operator (school staff), Supervisor (psychologist) and Admin
(program manager). We expose the role as both a first-class ``role``
field (for easy filtering in views) and as Django auth ``Groups`` (so
the built-in permission machinery keeps working). The two stay in sync
through ``User.save()``.
"""

from __future__ import annotations

from django.contrib.auth.models import AbstractUser, Group
from django.db import models


class Role(models.TextChoices):
    OPERATOR = "operator", "Operator (School staff)"
    SUPERVISOR = "supervisor", "Supervisor (Psychologist)"
    ADMIN = "admin", "Admin (Program manager)"


ROLE_GROUP_NAMES = {
    Role.OPERATOR: "Operators",
    Role.SUPERVISOR: "Supervisors",
    Role.ADMIN: "Program Admins",
}


class User(AbstractUser):
    """Application user with an explicit role.

    We keep Django's ``is_staff`` / ``is_superuser`` separate from our
    domain roles: a Supervisor is *not* a Django staff user, only
    platform ``Admin`` accounts created through the seed command are.
    """

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.OPERATOR,
        help_text="Platform role. Controls workflow actions, not Django admin access.",
    )
    school = models.CharField(
        max_length=100,
        blank=True,
        help_text="School / center the Operator works with (scopes visible students).",
    )
    region = models.CharField(
        max_length=80,
        blank=True,
        help_text="Administrative region (used by Admin dashboards).",
    )

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    # Convenience predicates used throughout the views -----------------
    @property
    def is_operator(self) -> bool:
        return self.role == Role.OPERATOR

    @property
    def is_supervisor(self) -> bool:
        return self.role == Role.SUPERVISOR

    @property
    def is_program_admin(self) -> bool:
        return self.role == Role.ADMIN

    def sync_groups(self) -> None:
        """Ensure the user belongs to exactly the group matching their role."""

        target_name = ROLE_GROUP_NAMES[Role(self.role)]
        target_group, _ = Group.objects.get_or_create(name=target_name)
        current = set(self.groups.values_list("name", flat=True))
        if current != {target_name}:
            self.groups.set([target_group])
