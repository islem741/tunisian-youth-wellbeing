"""Signals that keep Django groups aligned with the domain role field."""

from __future__ import annotations

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User


@receiver(post_save, sender=User)
def assign_role_group(sender, instance: User, created: bool, **kwargs) -> None:
    instance.sync_groups()
