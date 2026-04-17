"""Domain models for the case workflow.

The workflow follows the state diagram in ``docs/state_machine.md``::

    INTAKE -> ASSESSMENT -> INTERVENTION -> FOLLOW_UP -> CLOSED

Every transition is recorded in :class:`CaseEvent` so that the Supervisor
dashboard can display a human-readable timeline with author + timestamp
(Scenario 2 requirement). Validation is done in
:meth:`StressAssessment.clean` and must reject impossible scores with a
user-facing message (failure-injection requirement).
"""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils import timezone


# ---------------------------------------------------------------------------
# Risk policy (Supervisor-configurable threshold) ----------------------------
# ---------------------------------------------------------------------------
class RiskPolicy(models.Model):
    """Singleton row holding the configurable High-Risk threshold.

    Stored as a row so that updating it is auditable through Django's
    admin / ORM and so that different environments can start with their
    own policy fixtures. The Supervisor can change the value from the
    dashboard; the default falls back to ``settings.HIGH_RISK_THRESHOLD``.
    """

    threshold = models.PositiveSmallIntegerField(
        default=75,
        validators=[MinValueValidator(1), MaxValueValidator(300)],
        help_text="Total stress score at or above which a case is High Risk.",
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="risk_policies_edited",
    )

    class Meta:
        verbose_name = "Risk policy"
        verbose_name_plural = "Risk policies"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"High-Risk threshold = {self.threshold}"

    @classmethod
    def current(cls) -> "RiskPolicy":
        obj = cls.objects.first()
        if obj is None:
            default = getattr(settings, "HIGH_RISK_THRESHOLD", 75)
            obj = cls.objects.create(threshold=default)
        return obj


# ---------------------------------------------------------------------------
# Student ---------------------------------------------------------------------
# ---------------------------------------------------------------------------
class Student(models.Model):
    """A student the platform is tracking.

    Only synthetic identifiers are stored - see ``docs/data_dictionary.md``.
    """

    class Gender(models.TextChoices):
        FEMALE = "F", "Female"
        MALE = "M", "Male"
        OTHER = "O", "Other"

    external_id = models.CharField(
        max_length=32, unique=True, help_text="Synthetic opaque identifier."
    )
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    age = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(6), MaxValueValidator(25)]
    )
    gender = models.CharField(max_length=1, choices=Gender.choices, default=Gender.OTHER)
    grade = models.CharField(max_length=20, blank=True)
    school = models.CharField(max_length=100)
    region = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("last_name", "first_name")

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.last_name}, {self.first_name} ({self.external_id})"

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


# ---------------------------------------------------------------------------
# Workflow state --------------------------------------------------------------
# ---------------------------------------------------------------------------
class WorkflowState(models.TextChoices):
    INTAKE = "intake", "Intake"
    ASSESSMENT = "assessment", "Assessment"
    INTERVENTION = "intervention", "Intervention Planning"
    FOLLOW_UP = "follow_up", "Follow-up"
    CLOSED = "closed", "Closed"


# Allowed transitions - anything outside this map is rejected with a
# ``ValidationError`` and logged as a failure event.
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    WorkflowState.INTAKE: {WorkflowState.ASSESSMENT, WorkflowState.CLOSED},
    WorkflowState.ASSESSMENT: {WorkflowState.INTERVENTION, WorkflowState.CLOSED},
    WorkflowState.INTERVENTION: {WorkflowState.FOLLOW_UP, WorkflowState.CLOSED},
    WorkflowState.FOLLOW_UP: {WorkflowState.INTERVENTION, WorkflowState.CLOSED},
    WorkflowState.CLOSED: set(),
}


class RiskLevel(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High Risk"


# ---------------------------------------------------------------------------
# Stress assessment -----------------------------------------------------------
# ---------------------------------------------------------------------------
SCORE_VALIDATORS = [MinValueValidator(0), MaxValueValidator(100)]


class StressAssessment(models.Model):
    """A stress-level evaluation produced by an Operator.

    Scores are bounded to ``[0, 100]`` and the total is recomputed from
    its components on every save so that dashboards stay consistent even
    if a row is created through the Django admin or a fixture.
    """

    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="assessments"
    )
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="submitted_assessments",
        help_text="School staff member who produced the assessment.",
    )
    academic_pressure = models.PositiveSmallIntegerField(validators=SCORE_VALIDATORS)
    social_anxiety = models.PositiveSmallIntegerField(validators=SCORE_VALIDATORS)
    home_environment = models.PositiveSmallIntegerField(validators=SCORE_VALIDATORS)
    notes = models.TextField(blank=True)
    total_score = models.PositiveSmallIntegerField(editable=False, default=0)

    workflow_state = models.CharField(
        max_length=20,
        choices=WorkflowState.choices,
        default=WorkflowState.INTAKE,
    )
    risk_level = models.CharField(
        max_length=10,
        choices=RiskLevel.choices,
        default=RiskLevel.LOW,
    )
    risk_explanation = models.TextField(
        blank=True,
        help_text=(
            "Human-readable reason why the risk level was assigned."
            " Populated automatically by the rule engine."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("workflow_state", "risk_level")),
            models.Index(fields=("-created_at",)),
        ]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Assessment<{self.student.external_id} total={self.total_score}>"

    # ------------------------------------------------------------------ helpers
    @property
    def components(self) -> dict[str, int]:
        return {
            "Academic pressure": self.academic_pressure,
            "Social anxiety": self.social_anxiety,
            "Home environment": self.home_environment,
        }

    def clean(self) -> None:
        """Reject impossible score values with a friendly message.

        Scenario 2 / Failure-injection requirement: a stress score of
        ``-5`` or ``150`` must *not* crash the application; instead, a
        ``ValidationError`` with a user-facing message is raised.
        """

        super().clean()
        bad_fields = [
            name
            for name, value in {
                "academic_pressure": self.academic_pressure,
                "social_anxiety": self.social_anxiety,
                "home_environment": self.home_environment,
            }.items()
            if value is None or value < 0 or value > 100
        ]
        if bad_fields:
            raise ValidationError(
                {
                    field: (
                        "Score must be an integer between 0 and 100."
                    )
                    for field in bad_fields
                }
            )

    def compute_total(self) -> int:
        return int(self.academic_pressure + self.social_anxiety + self.home_environment)

    def evaluate_risk(self, threshold: int | None = None) -> tuple[str, str]:
        """Return ``(risk_level, explanation)`` using the current policy."""

        if threshold is None:
            threshold = RiskPolicy.current().threshold
        total = self.compute_total()
        breakdown = (
            f"academic pressure {self.academic_pressure}, "
            f"social anxiety {self.social_anxiety}, "
            f"home environment {self.home_environment}"
        )
        if total >= threshold:
            return (
                RiskLevel.HIGH,
                (
                    f"Total stress score {total} reached the configured "
                    f"High-Risk threshold of {threshold}. "
                    f"Component breakdown: {breakdown}."
                ),
            )
        if total >= threshold * 0.7:
            return (
                RiskLevel.MEDIUM,
                (
                    f"Total stress score {total} is approaching the "
                    f"High-Risk threshold of {threshold}. "
                    f"Component breakdown: {breakdown}."
                ),
            )
        return (
            RiskLevel.LOW,
            (
                f"Total stress score {total} is well below the "
                f"High-Risk threshold of {threshold}. "
                f"Component breakdown: {breakdown}."
            ),
        )

    def save(self, *args, **kwargs):
        # Running full_clean() here protects the data layer even when a
        # row is added via the admin or a fixture.
        self.full_clean()
        self.total_score = self.compute_total()
        level, explanation = self.evaluate_risk()
        self.risk_level = level
        self.risk_explanation = explanation
        # If the assessment is freshly created and already flags as High
        # Risk, automatically move the workflow into Assessment so that
        # a Supervisor immediately sees it on their queue.
        if self._state.adding and self.risk_level == RiskLevel.HIGH:
            self.workflow_state = WorkflowState.ASSESSMENT
        super().save(*args, **kwargs)

    # ------------------------------------------------------------------ transitions
    def transition_to(self, new_state: str, *, actor, reason: str = "") -> "CaseEvent":
        """Move the case to ``new_state``, enforcing the state machine."""

        new_state = WorkflowState(new_state).value
        current = WorkflowState(self.workflow_state).value
        if new_state not in ALLOWED_TRANSITIONS[current]:
            raise ValidationError(
                f"Illegal transition {current} -> {new_state}."
            )
        with transaction.atomic():
            old_state = self.workflow_state
            self.workflow_state = new_state
            self.save(update_fields=["workflow_state", "updated_at"])
            event = CaseEvent.objects.create(
                assessment=self,
                actor=actor,
                action=CaseEvent.Action.STATE_CHANGE,
                from_state=old_state,
                to_state=new_state,
                detail=reason or f"Moved case to {new_state}.",
            )
        return event


# ---------------------------------------------------------------------------
# Intervention appointments --------------------------------------------------
# ---------------------------------------------------------------------------
class Appointment(models.Model):
    """An intervention / follow-up appointment for a case.

    Scenario 2 requires that when an appointment is flagged as ``MISSED``
    the system automatically creates a ``REMINDER`` case event.
    """

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        COMPLETED = "completed", "Completed"
        MISSED = "missed", "Missed"
        CANCELLED = "cancelled", "Cancelled"

    assessment = models.ForeignKey(
        StressAssessment, on_delete=models.CASCADE, related_name="appointments"
    )
    scheduled_for = models.DateTimeField()
    scheduled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="scheduled_appointments",
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.SCHEDULED
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("scheduled_for",)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"Appointment<{self.assessment_id} {self.status}>"

    def mark_missed(self, *, actor) -> "CaseEvent":
        if self.status == self.Status.MISSED:
            # Idempotent: calling twice shouldn't generate a duplicate.
            return self.assessment.events.filter(
                action=CaseEvent.Action.REMINDER, detail__contains=str(self.pk)
            ).first() or self._log_missed(actor)
        self.status = self.Status.MISSED
        self.save(update_fields=["status", "updated_at"])
        return self._log_missed(actor)

    def _log_missed(self, actor) -> "CaseEvent":
        CaseEvent.objects.create(
            assessment=self.assessment,
            actor=actor,
            action=CaseEvent.Action.APPOINTMENT,
            detail=(
                f"Appointment #{self.pk} scheduled for "
                f"{self.scheduled_for:%Y-%m-%d %H:%M} was marked Missed."
            ),
        )
        reminder = CaseEvent.objects.create(
            assessment=self.assessment,
            actor=actor,
            action=CaseEvent.Action.REMINDER,
            detail=(
                f"Automatic reminder queued for missed appointment "
                f"#{self.pk} ({self.assessment.student.display_name})."
            ),
        )
        return reminder


# ---------------------------------------------------------------------------
# Case timeline events -------------------------------------------------------
# ---------------------------------------------------------------------------
class CaseEvent(models.Model):
    """Immutable audit entry for a case.

    Every workflow-relevant action goes through ``CaseEvent.objects.create``
    so that the timeline view can answer the Scenario 2 question
    "who did what and when".
    """

    class Action(models.TextChoices):
        INTAKE = "intake", "Case created"
        STATE_CHANGE = "state_change", "State change"
        APPOINTMENT = "appointment", "Appointment update"
        REMINDER = "reminder", "Automatic reminder"
        NOTE = "note", "Note added"
        DENIED = "denied", "Action denied"

    assessment = models.ForeignKey(
        StressAssessment, on_delete=models.CASCADE, related_name="events"
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="case_events",
    )
    action = models.CharField(max_length=20, choices=Action.choices)
    from_state = models.CharField(max_length=20, blank=True)
    to_state = models.CharField(max_length=20, blank=True)
    detail = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.action} by {self.actor} @ {self.created_at:%Y-%m-%d %H:%M}"

    @property
    def human_summary(self) -> str:
        """Friendly single-line summary for the timeline template."""

        actor = self.actor.get_full_name() or self.actor.username if self.actor else "System"
        if self.action == self.Action.STATE_CHANGE:
            return f"{actor} moved case from {self.from_state} to {self.to_state}."
        if self.action == self.Action.REMINDER:
            return f"System queued an automatic reminder ({self.detail})."
        if self.action == self.Action.DENIED:
            return f"Blocked action by {actor}: {self.detail}"
        return f"{actor}: {self.detail or self.get_action_display()}"
