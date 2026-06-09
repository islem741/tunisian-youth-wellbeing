"""Domain models for the Youth Mental Health Peer-Support Platform.

Four models:
  MoodScore      — self-reported mood entry by a Youth
  Assignment     — links a Peer Supporter to a Youth (+ optional Counselor)
  SupportSession — logged peer-support interaction, with escalation support
  AuditEvent     — immutable audit log (replaces CaseEvent)
"""

from __future__ import annotations

from datetime import date

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# MoodScore ------------------------------------------------------------------
# ---------------------------------------------------------------------------
class MoodScore(models.Model):
    """A single self-reported mood entry submitted by a Youth (1–10 scale)."""

    youth = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mood_scores",
    )
    score = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Self-reported mood score from 1 (very low) to 10 (very high).",
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:  # pragma: no cover
        return f"MoodScore<youth={self.youth_id} score={self.score}>"

    @classmethod
    def check_consecutive_low(
        cls, youth, threshold: int = 3, low_cutoff: int = 4
    ) -> bool:
        """Return True if the last ``threshold`` scores are all <= ``low_cutoff``."""
        recent = list(
            cls.objects.filter(youth=youth)
            .order_by("-created_at")
            .values_list("score", flat=True)[:threshold]
        )
        return len(recent) == threshold and all(s <= low_cutoff for s in recent)


# ---------------------------------------------------------------------------
# Assignment -----------------------------------------------------------------
# ---------------------------------------------------------------------------
class Assignment(models.Model):
    """Links a Peer Supporter to a Youth, optionally with a Counselor."""

    youth = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assignments_as_youth",
    )
    peer_supporter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="assignments_as_supporter",
    )
    counselor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_cases",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = (("youth", "peer_supporter"),)

    def __str__(self) -> str:  # pragma: no cover
        return f"Assignment<youth={self.youth_id} supporter={self.peer_supporter_id}>"


# ---------------------------------------------------------------------------
# SupportSession -------------------------------------------------------------
# ---------------------------------------------------------------------------
class SupportSession(models.Model):
    """A logged peer-support interaction, with optional escalation."""

    class EscalationStatus(models.TextChoices):
        NONE     = "none",     "No escalation"
        PENDING  = "pending",  "Pending counselor review"
        RESOLVED = "resolved", "Resolved"

    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name="sessions",
    )
    logged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="logged_sessions",
    )
    session_date = models.DateField(default=date.today)
    notes = models.TextField()
    mood_at_session = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Youth's mood score at time of session (1–10).",
    )
    escalation_status = models.CharField(
        max_length=10,
        choices=EscalationStatus.choices,
        default=EscalationStatus.NONE,
    )
    escalated_at = models.DateTimeField(null=True, blank=True)
    escalated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="escalated_sessions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-session_date", "-created_at")

    def __str__(self) -> str:  # pragma: no cover
        return f"SupportSession<{self.pk} {self.escalation_status}>"

    def escalate(self, actor) -> None:
        """Mark session as PENDING escalation and record who/when."""
        self.escalation_status = self.EscalationStatus.PENDING
        self.escalated_at = timezone.now()
        self.escalated_by = actor
        self.save(
            update_fields=[
                "escalation_status",
                "escalated_at",
                "escalated_by",
                "updated_at",
            ]
        )
        AuditEvent.objects.create(
            actor=actor,
            action=AuditEvent.Action.ESCALATION,
            detail=f"Session #{self.pk} escalated to counselor.",
            youth=self.assignment.youth,
        )


# ---------------------------------------------------------------------------
# AuditEvent -----------------------------------------------------------------
# ---------------------------------------------------------------------------
class AuditEvent(models.Model):
    """Immutable audit log entry for all platform-relevant actions."""

    class Action(models.TextChoices):
        MOOD_LOG         = "mood_log",        "Mood score logged"
        SESSION_LOG      = "session_log",     "Session logged"
        ESCALATION       = "escalation",      "Escalation triggered"
        AUTO_ESCALATION  = "auto_escalation", "Auto-escalation (3× low mood)"
        ACCESS_DENIED    = "access_denied",   "Unauthorized access attempt"
        SUPERVISOR_ALERT = "supervisor_alert","Supervisor notified"
        ASSIGNMENT       = "assignment",      "Assignment changed"

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events_as_actor",
    )
    youth = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:  # pragma: no cover
        return f"{self.action} @ {self.created_at:%Y-%m-%d %H:%M}"

    @property
    def human_summary(self) -> str:
        actor_name = (
            self.actor.get_full_name() or self.actor.username
            if self.actor
            else "System"
        )
        return f"{actor_name}: {self.get_action_display()} — {self.detail}"
