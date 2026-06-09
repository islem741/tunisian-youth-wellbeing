import datetime

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MoodScore",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("score", models.PositiveSmallIntegerField(
                    help_text="Self-reported mood score from 1 (very low) to 10 (very high).",
                    validators=[
                        django.core.validators.MinValueValidator(1),
                        django.core.validators.MaxValueValidator(10),
                    ],
                )),
                ("note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("youth", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="mood_scores",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="Assignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("is_active", models.BooleanField(default=True)),
                ("counselor", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="assigned_cases",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("peer_supporter", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="assignments_as_supporter",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("youth", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="assignments_as_youth",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"unique_together": {("youth", "peer_supporter")}},
        ),
        migrations.CreateModel(
            name="SupportSession",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("session_date", models.DateField(default=datetime.date.today)),
                ("notes", models.TextField()),
                ("mood_at_session", models.PositiveSmallIntegerField(
                    blank=True, null=True,
                    help_text="Youth's mood score at time of session (1–10).",
                    validators=[
                        django.core.validators.MinValueValidator(1),
                        django.core.validators.MaxValueValidator(10),
                    ],
                )),
                ("escalation_status", models.CharField(
                    choices=[
                        ("none", "No escalation"),
                        ("pending", "Pending counselor review"),
                        ("resolved", "Resolved"),
                    ],
                    default="none",
                    max_length=10,
                )),
                ("escalated_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assignment", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="sessions",
                    to="support.assignment",
                )),
                ("escalated_by", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="escalated_sessions",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("logged_by", models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name="logged_sessions",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"ordering": ("-session_date", "-created_at")},
        ),
        migrations.CreateModel(
            name="AuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(
                    choices=[
                        ("mood_log", "Mood score logged"),
                        ("session_log", "Session logged"),
                        ("escalation", "Escalation triggered"),
                        ("auto_escalation", "Auto-escalation (3× low mood)"),
                        ("access_denied", "Unauthorized access attempt"),
                        ("supervisor_alert", "Supervisor notified"),
                        ("assignment", "Assignment changed"),
                    ],
                    max_length=20,
                )),
                ("detail", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("actor", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="audit_events_as_actor",
                    to=settings.AUTH_USER_MODEL,
                )),
                ("youth", models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name="audit_events",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={"ordering": ("-created_at",)},
        ),
    ]
