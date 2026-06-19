"""DRF serializers for the cases API (read-only)."""

from __future__ import annotations

from rest_framework import serializers

from cases.models import CaseEvent, SERSEntry, Student


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Student
        fields = ("external_id", "first_name", "last_name", "age", "school", "region")


class SERSEntrySerializer(serializers.ModelSerializer):
    student = StudentSerializer(read_only=True)

    class Meta:
        model  = SERSEntry
        fields = (
            "id",
            "student",
            "sers_score",
            "risk_level",
            "risk_explanation",
            "workflow_state",
            "created_at",
        )


class CaseEventSerializer(serializers.ModelSerializer):
    actor = serializers.SerializerMethodField()

    class Meta:
        model  = CaseEvent
        fields = ("action", "actor", "from_state", "to_state", "detail", "created_at")

    def get_actor(self, obj) -> str | None:
        return obj.actor.username if obj.actor else None
