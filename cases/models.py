"""Domain models for the Student Early-Warning & Well-Being platform.

Workflow: INTAKE → ASSESSMENT → INTERVENTION → FOLLOW_UP → CLOSED

Every transition is recorded in CaseEvent (immutable audit log).
The SERS (Student Engagement Risk Score) is computed by the service
layer in cases.services, not here, to keep models thin and testable.
"""

from __future__ import annotations

from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.utils import timezone


# ---------------------------------------------------------------------------
# SERSPolicy — Admin-configurable weights and thresholds
# ---------------------------------------------------------------------------
class SERSPolicy(models.Model):
    """Singleton row: Admin configures SERS weights and risk thresholds."""

    absence_weight    = models.PositiveSmallIntegerField(default=6)
    grade_drop_weight = models.PositiveSmallIntegerField(default=5)
    behavior_weight   = models.PositiveSmallIntegerField(default=8)
    wellbeing_weight  = models.PositiveSmallIntegerField(default=10)
    high_threshold    = models.PositiveSmallIntegerField(
        default=65,
        help_text="SERS >= this value → HIGH risk.",
    )
    medium_threshold  = models.PositiveSmallIntegerField(
        default=40,
        help_text="SERS >= this value (and < high) → MEDIUM risk.",
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="sers_policies_edited",
    )

    class Meta:
        verbose_name = "SERS Policy"
        verbose_name_plural = "SERS Policies"

    def __str__(self):
        return (
            f"SERS Policy — high≥{self.high_threshold}, "
            f"medium≥{self.medium_threshold}"
        )

    def clean(self):
        if self.medium_threshold >= self.high_threshold:
            raise ValidationError(
                "Medium threshold must be strictly less than High threshold."
            )
        total_weight = (
            self.absence_weight + self.grade_drop_weight
            + self.behavior_weight + self.wellbeing_weight
        )
        if total_weight == 0:
            raise ValidationError("At least one weight must be > 0.")

    @classmethod
    def current(cls) -> "SERSPolicy":
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create()
        return obj


# ---------------------------------------------------------------------------
# Student
# ---------------------------------------------------------------------------
class Student(models.Model):
    class Gender(models.TextChoices):
        FEMALE = "F", "Female"
        MALE   = "M", "Male"
        OTHER  = "O", "Other / Not specified"

    external_id = models.CharField(
        max_length=32, unique=True,
        help_text="Synthetic opaque identifier (e.g. STU-0001-TUN).",
    )
    first_name  = models.CharField(max_length=50)
    last_name   = models.CharField(max_length=50)
    age         = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(10), MaxValueValidator(20)],
    )
    gender      = models.CharField(
        max_length=1, choices=Gender.choices, default=Gender.OTHER,
    )
    grade       = models.CharField(
        max_length=20, blank=True,
        help_text="Grade / class level (e.g. '9e', '2ème Sec').",
    )
    school      = models.CharField(max_length=100)
    region      = models.CharField(
        max_length=80,
        help_text="Tunisian governorate.",
    )
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("last_name", "first_name")

    def __str__(self):
        return f"{self.last_name}, {self.first_name} ({self.external_id})"

    @property
    def display_name(self):
        return f"{self.first_name} {self.last_name}"


# ---------------------------------------------------------------------------
# WorkflowState & RiskLevel
# ---------------------------------------------------------------------------
class WorkflowState(models.TextChoices):
    INTAKE       = "intake",       "Intake"
    ASSESSMENT   = "assessment",   "Assessment"
    INTERVENTION = "intervention", "Intervention Planning"
    FOLLOW_UP    = "follow_up",    "Follow-up"
    CLOSED       = "closed",       "Closed"


ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    WorkflowState.INTAKE:       {WorkflowState.ASSESSMENT, WorkflowState.CLOSED},
    WorkflowState.ASSESSMENT:   {WorkflowState.INTERVENTION, WorkflowState.CLOSED},
    WorkflowState.INTERVENTION: {WorkflowState.FOLLOW_UP, WorkflowState.CLOSED},
    WorkflowState.FOLLOW_UP:    {WorkflowState.INTERVENTION, WorkflowState.CLOSED},
    WorkflowState.CLOSED:       set(),
}


class RiskLevel(models.TextChoices):
    LOW    = "low",    "Low"
    MEDIUM = "medium", "Medium"
    HIGH   = "high",   "High Risk"


# ---------------------------------------------------------------------------
# SERSEntry — one SERS submission per student per period
# ---------------------------------------------------------------------------
class SERSEntry(models.Model):
    """A single SERS data submission produced by an Operator."""

    student      = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name="sers_entries",
    )
    operator     = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT, related_name="submitted_entries",
        help_text="Operator who submitted this entry.",
    )
    period_label = models.CharField(
        max_length=30, blank=True,
        help_text="e.g. 'Week 12 / 2025' or 'March 2025'.",
    )

    # Raw input components
    unexcused_absences = models.PositiveSmallIntegerField(
        default=0, validators=[MaxValueValidator(30)],
    )
    grade_drop_points  = models.PositiveSmallIntegerField(
        default=0, validators=[MaxValueValidator(20)],
        help_text="Points dropped from previous period average (0–20).",
    )
    disciplinary_flags = models.PositiveSmallIntegerField(
        default=0, validators=[MaxValueValidator(10)],
    )
    wellbeing_score    = models.PositiveSmallIntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text="Self-reported or staff-observed well-being (1=very low, 10=excellent).",
    )
    notes = models.TextField(blank=True)

    # Computed fields (set by save())
    sers_score       = models.PositiveSmallIntegerField(editable=False, default=0)
    risk_level       = models.CharField(
        max_length=10, choices=RiskLevel.choices, default=RiskLevel.LOW,
    )
    risk_explanation = models.TextField(blank=True, editable=False)

    # Workflow
    workflow_state = models.CharField(
        max_length=20, choices=WorkflowState.choices,
        default=WorkflowState.INTAKE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "SERS Entry"
        verbose_name_plural = "SERS Entries"
        indexes = [
            models.Index(fields=("workflow_state", "risk_level")),
            models.Index(fields=("-created_at",)),
        ]

    def __str__(self):
        return (
            f"SERS<{self.student.external_id} "
            f"score={self.sers_score} {self.risk_level}>"
        )

    def clean(self):
        """Reject out-of-range component values with user-facing messages."""
        super().clean()
        errors = {}
        if not (0 <= self.unexcused_absences <= 30):
            errors["unexcused_absences"] = "Must be between 0 and 30."
        if not (0 <= self.grade_drop_points <= 20):
            errors["grade_drop_points"] = "Must be between 0 and 20."
        if not (0 <= self.disciplinary_flags <= 10):
            errors["disciplinary_flags"] = "Must be between 0 and 10."
        if not (1 <= self.wellbeing_score <= 10):
            errors["wellbeing_score"] = "Must be between 1 and 10."
        if errors:
            raise ValidationError(errors)

    def compute_sers(self, policy: SERSPolicy | None = None) -> tuple[int, str]:
        """Return (score 0-100, explanation) using the current SERSPolicy."""
        if policy is None:
            policy = SERSPolicy.current()
        # Invert wellbeing: score 1 = worst → component 9; score 10 = best → 0
        wellbeing_component = max(0, 10 - self.wellbeing_score)
        raw = (
            policy.absence_weight    * self.unexcused_absences
            + policy.grade_drop_weight * self.grade_drop_points
            + policy.behavior_weight   * self.disciplinary_flags
            + policy.wellbeing_weight  * wellbeing_component
        )
        score = min(100, raw)
        explanation = (
            f"Absences {self.unexcused_absences}×{policy.absence_weight}"
            f"={policy.absence_weight * self.unexcused_absences} pts; "
            f"grade drop {self.grade_drop_points}×{policy.grade_drop_weight}"
            f"={policy.grade_drop_weight * self.grade_drop_points} pts; "
            f"behavior {self.disciplinary_flags}×{policy.behavior_weight}"
            f"={policy.behavior_weight * self.disciplinary_flags} pts; "
            f"well-being (inverted {wellbeing_component})×{policy.wellbeing_weight}"
            f"={policy.wellbeing_weight * wellbeing_component} pts. "
            f"Total (capped at 100): {score}."
        )
        return score, explanation

    def evaluate_risk(self, policy: SERSPolicy | None = None) -> tuple[str, str]:
        if policy is None:
            policy = SERSPolicy.current()
        score, explanation = self.compute_sers(policy)
        if score >= policy.high_threshold:
            return RiskLevel.HIGH, explanation
        if score >= policy.medium_threshold:
            return RiskLevel.MEDIUM, explanation
        return RiskLevel.LOW, explanation

    def save(self, *args, **kwargs):
        self.full_clean()
        policy = SERSPolicy.current()
        self.sers_score, _ = self.compute_sers(policy)
        self.risk_level, self.risk_explanation = self.evaluate_risk(policy)
        if self._state.adding and self.risk_level == RiskLevel.HIGH:
            self.workflow_state = WorkflowState.ASSESSMENT
        super().save(*args, **kwargs)

    def transition_to(
        self, new_state: str, *, actor, reason: str = ""
    ) -> "CaseEvent":
        new_state = WorkflowState(new_state).value
        current   = WorkflowState(self.workflow_state).value
        if new_state not in ALLOWED_TRANSITIONS[current]:
            raise ValidationError(
                f"Illegal transition {current} → {new_state}."
            )
        with transaction.atomic():
            old_state = self.workflow_state
            self.workflow_state = new_state
            self.save(update_fields=["workflow_state", "updated_at"])
            event = CaseEvent.objects.create(
                entry=self, actor=actor,
                action=CaseEvent.Action.STATE_CHANGE,
                from_state=old_state, to_state=new_state,
                detail=reason or f"Moved to {new_state}.",
            )
        return event


# ---------------------------------------------------------------------------
# InterventionPlan
# ---------------------------------------------------------------------------
class InterventionPlan(models.Model):
    class PlanType(models.TextChoices):
        PARENT_MEETING = "parent_meeting", "Parent Meeting"
        TUTORING       = "tutoring",       "Tutoring"
        COUNSELING     = "counseling",     "Counselor Session"
        REFERRAL       = "referral",       "External Referral"
        OTHER          = "other",          "Other"

    class PlanStatus(models.TextChoices):
        PENDING   = "pending",   "Pending"
        ACTIVE    = "active",    "Active"
        COMPLETED = "completed", "Completed"
        ESCALATED = "escalated", "Escalated"

    entry       = models.ForeignKey(
        SERSEntry, on_delete=models.CASCADE, related_name="interventions",
    )
    plan_type   = models.CharField(
        max_length=20, choices=PlanType.choices, default=PlanType.COUNSELING,
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT, related_name="assigned_interventions",
        help_text="Supervisor responsible for this intervention.",
    )
    due_date    = models.DateField(default=date.today)
    status      = models.CharField(
        max_length=12, choices=PlanStatus.choices, default=PlanStatus.PENDING,
    )
    notes      = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("due_date",)
        verbose_name = "Intervention Plan"

    def __str__(self):
        return f"{self.get_plan_type_display()} for entry #{self.entry_id}"

    def mark_completed(self, *, actor) -> "CaseEvent":
        self.status = self.PlanStatus.COMPLETED
        self.save(update_fields=["status", "updated_at"])
        return CaseEvent.objects.create(
            entry=self.entry, actor=actor,
            action=CaseEvent.Action.INTERVENTION,
            detail=f"Intervention '{self.get_plan_type_display()}' marked completed.",
        )


# ---------------------------------------------------------------------------
# CaseEvent — immutable audit log
# ---------------------------------------------------------------------------
class CaseEvent(models.Model):
    class Action(models.TextChoices):
        INTAKE       = "intake",       "Case created"
        STATE_CHANGE = "state_change", "State change"
        INTERVENTION = "intervention", "Intervention update"
        REMINDER     = "reminder",     "Automatic reminder"
        NOTE         = "note",         "Note added"
        DENIED       = "denied",       "Action denied"
        SECURITY     = "security",     "Security event"

    entry      = models.ForeignKey(
        SERSEntry, on_delete=models.CASCADE, related_name="events",
    )
    actor      = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL, related_name="case_events",
    )
    action     = models.CharField(max_length=20, choices=Action.choices)
    from_state = models.CharField(max_length=20, blank=True)
    to_state   = models.CharField(max_length=20, blank=True)
    detail     = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.action} by {self.actor} @ {self.created_at:%Y-%m-%d %H:%M}"

    @property
    def human_summary(self) -> str:
        actor = (
            self.actor.get_full_name() or self.actor.username
            if self.actor else "System"
        )
        if self.action == self.Action.STATE_CHANGE:
            return f"{actor} moved case {self.from_state} → {self.to_state}."
        if self.action == self.Action.REMINDER:
            return f"System: {self.detail}"
        if self.action == self.Action.DENIED:
            return f"BLOCKED — {actor}: {self.detail}"
        if self.action == self.Action.SECURITY:
            return f"SECURITY — {actor}: {self.detail}"
        return f"{actor}: {self.detail or self.get_action_display()}"
