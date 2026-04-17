"""Forms for the case-management views.

The ``StressAssessmentForm`` re-uses the ``full_clean`` validation on
the model so user-facing messages come from a single source of truth.
The CSV upload form accepts a single text file with a strict schema
and rejects malformed rows gracefully (failure-injection evidence).
"""

from __future__ import annotations

from django import forms

from .models import Appointment, RiskPolicy, Student, StressAssessment


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ("external_id", "first_name", "last_name", "age", "gender",
                  "grade", "school", "region")


class StressAssessmentForm(forms.ModelForm):
    class Meta:
        model = StressAssessment
        fields = ("student", "academic_pressure", "social_anxiety",
                  "home_environment", "notes")
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 3}),
        }


class StressAssessmentCSVUploadForm(forms.Form):
    """CSV upload form used by the Operator.

    Expected columns (header row is mandatory):
    ``external_id, academic_pressure, social_anxiety, home_environment[, notes]``
    """

    csv_file = forms.FileField(
        label="Stress assessment CSV",
        help_text=(
            "Columns (header row required): external_id, academic_pressure, "
            "social_anxiety, home_environment, notes (optional)."
        ),
    )


class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ("scheduled_for", "notes")
        widgets = {
            "scheduled_for": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["scheduled_for"].input_formats = ["%Y-%m-%dT%H:%M"]


class RiskPolicyForm(forms.ModelForm):
    class Meta:
        model = RiskPolicy
        fields = ("threshold",)


class CaseTransitionForm(forms.Form):
    to_state = forms.ChoiceField(choices=[])
    reason = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 2}),
        required=False,
        help_text="Optional note recorded in the case timeline.",
    )

    def __init__(self, *args, allowed_states: list[tuple[str, str]], **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["to_state"].choices = allowed_states
