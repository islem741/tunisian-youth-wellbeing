"""Forms for the support app."""

from __future__ import annotations

from django import forms

from .models import Assignment, MoodScore, SupportSession


class MoodScoreForm(forms.ModelForm):
    class Meta:
        model = MoodScore
        fields = ("score", "note")
        widgets = {
            "score": forms.NumberInput(
                attrs={"type": "range", "min": 1, "max": 10, "step": 1}
            ),
            "note": forms.Textarea(attrs={"rows": 3}),
        }


class SupportSessionForm(forms.ModelForm):
    class Meta:
        model = SupportSession
        fields = ("session_date", "notes", "mood_at_session")
        widgets = {
            "session_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 4}),
            "mood_at_session": forms.NumberInput(attrs={"min": 1, "max": 10}),
        }


class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ("youth", "peer_supporter", "counselor")
