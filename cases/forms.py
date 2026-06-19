from __future__ import annotations

from django import forms

from .models import InterventionPlan, SERSEntry, SERSPolicy, Student


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = (
            "external_id", "first_name", "last_name", "age",
            "gender", "grade", "school", "region",
        )


class SERSEntryForm(forms.ModelForm):
    """Used by Operators to submit a single SERS entry."""

    class Meta:
        model = SERSEntry
        fields = (
            "student", "period_label", "unexcused_absences",
            "grade_drop_points", "disciplinary_flags",
            "wellbeing_score", "notes",
        )
        widgets = {
            "notes":          forms.Textarea(attrs={"rows": 3}),
            "period_label":   forms.TextInput(
                attrs={"placeholder": "e.g. Week 12 / 2025"}
            ),
            "wellbeing_score": forms.NumberInput(attrs={"min": 1, "max": 10}),
        }
        help_texts = {
            "wellbeing_score": (
                "1 = very low, 10 = excellent (self-reported or staff-observed)."
            ),
            "grade_drop_points": (
                "Points dropped from previous period average (0–20)."
            ),
        }


class SERSCSVUploadForm(forms.Form):
    """CSV bulk-upload form used by Operators."""

    csv_file = forms.FileField(
        label="SERS data CSV",
        help_text=(
            "Required columns (header row mandatory): "
            "external_id, unexcused_absences, grade_drop_points, "
            "disciplinary_flags, wellbeing_score. "
            "Optional: notes, period_label."
        ),
    )
    period_label = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "e.g. March 2025"}),
        help_text=(
            "Applied to all rows that don't have their own period_label column."
        ),
    )


class CaseTransitionForm(forms.Form):
    to_state = forms.ChoiceField(choices=[])
    reason   = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False,
        help_text="Optional note recorded in the case timeline.",
    )

    def __init__(self, *args, allowed_states: list[tuple[str, str]], **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["to_state"].choices = allowed_states


class InterventionPlanForm(forms.ModelForm):
    class Meta:
        model = InterventionPlan
        fields = ("plan_type", "assigned_to", "due_date", "notes")
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "notes":    forms.Textarea(attrs={"rows": 3}),
        }


class SERSPolicyForm(forms.ModelForm):
    class Meta:
        model = SERSPolicy
        fields = (
            "absence_weight", "grade_drop_weight", "behavior_weight",
            "wellbeing_weight", "high_threshold", "medium_threshold",
        )
        help_texts = {
            "high_threshold":   "SERS ≥ this value → HIGH risk.",
            "medium_threshold": "SERS ≥ this value (and below high) → MEDIUM risk.",
        }
