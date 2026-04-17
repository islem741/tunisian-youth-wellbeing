"""Seed the database with synthetic users, students and assessments.

Run it with::

    python manage.py seed_demo_data

It is idempotent: running twice will not create duplicate users or
students. It is the only supported way to populate the demo data set.
"""

from __future__ import annotations

import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from faker import Faker

from accounts.models import Role
from cases.models import (
    Appointment,
    CaseEvent,
    RiskPolicy,
    Student,
    StressAssessment,
    WorkflowState,
)

User = get_user_model()

DEMO_PASSWORD = "demopass123"


SCHOOLS = [
    ("Lycée Pilote Tunis", "Tunis"),
    ("Collège El Khadra", "Ariana"),
    ("Lycée Ibn Khaldoun", "Sousse"),
    ("Collège Hannibal", "Bizerte"),
]


class Command(BaseCommand):
    help = "Create the demo users, students and synthetic stress assessments."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--students", type=int, default=40,
            help="Total number of synthetic students to create (default: 40)",
        )
        parser.add_argument(
            "--assessments", type=int, default=60,
            help="Total number of stress assessments to create (default: 60)",
        )
        parser.add_argument(
            "--seed", type=int, default=42,
            help="Seed for the random generator, for reproducibility (default: 42)",
        )

    @transaction.atomic
    def handle(self, *args, **options) -> None:
        seed = options["seed"]
        random.seed(seed)
        faker = Faker()
        Faker.seed(seed)

        # Users ---------------------------------------------------------
        operator = self._ensure_user(
            username="operator1",
            role=Role.OPERATOR,
            first="Amine", last="Ben Salah",
            school=SCHOOLS[0][0], region=SCHOOLS[0][1],
            is_staff=False,
        )
        operator2 = self._ensure_user(
            username="operator2",
            role=Role.OPERATOR,
            first="Hela", last="Trabelsi",
            school=SCHOOLS[1][0], region=SCHOOLS[1][1],
            is_staff=False,
        )
        supervisor = self._ensure_user(
            username="supervisor1",
            role=Role.SUPERVISOR,
            first="Dr. Nadia", last="Ouali",
            school="", region="Tunis",
            is_staff=False,
        )
        admin = self._ensure_user(
            username="admin1",
            role=Role.ADMIN,
            first="Kamel", last="Haddad",
            school="", region="",
            is_staff=True, is_superuser=True,
        )

        RiskPolicy.current()  # make sure the policy row exists

        # Students ------------------------------------------------------
        existing = Student.objects.count()
        wanted = options["students"]
        for _ in range(max(0, wanted - existing)):
            school, region = random.choice(SCHOOLS)
            Student.objects.create(
                external_id=faker.unique.bothify(text="STU-####-???"),
                first_name=faker.first_name(),
                last_name=faker.last_name(),
                age=random.randint(11, 18),
                gender=random.choice(["F", "M", "O"]),
                grade=random.choice(["7", "8", "9", "10", "11", "12"]),
                school=school,
                region=region,
            )

        students = list(Student.objects.all())

        # Assessments ---------------------------------------------------
        for _ in range(options["assessments"]):
            student = random.choice(students)
            ap = random.randint(10, 95)
            sa = random.randint(10, 95)
            he = random.randint(5, 95)
            operator_obj = operator if student.school == operator.school else operator2
            assessment = StressAssessment.objects.create(
                student=student,
                operator=operator_obj,
                academic_pressure=ap,
                social_anxiety=sa,
                home_environment=he,
                notes=faker.sentence(),
            )
            CaseEvent.objects.create(
                assessment=assessment,
                actor=operator_obj,
                action=CaseEvent.Action.INTAKE,
                to_state=assessment.workflow_state,
                detail=(
                    f"Synthetic intake. Risk level: "
                    f"{assessment.get_risk_level_display()}."
                ),
            )

        # Demo appointments for a couple of the high-risk cases --------
        high_cases = StressAssessment.objects.filter(
            workflow_state=WorkflowState.ASSESSMENT
        )[:3]
        for case in high_cases:
            case.transition_to(
                WorkflowState.INTERVENTION,
                actor=supervisor,
                reason="Escalated to intervention planning (demo data).",
            )
            appt = Appointment.objects.create(
                assessment=case,
                scheduled_for=timezone.now() - timedelta(days=2),
                scheduled_by=supervisor,
                notes="Initial counseling session.",
            )
            appt.mark_missed(actor=supervisor)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded users (password='{DEMO_PASSWORD}'), "
            f"{Student.objects.count()} students, "
            f"{StressAssessment.objects.count()} assessments."
        ))

    # -----------------------------------------------------------------
    def _ensure_user(
        self,
        *,
        username: str,
        role: str,
        first: str,
        last: str,
        school: str,
        region: str,
        is_staff: bool = False,
        is_superuser: bool = False,
    ) -> User:
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "first_name": first,
                "last_name": last,
                "role": role,
                "school": school,
                "region": region,
                "is_staff": is_staff,
                "is_superuser": is_superuser,
            },
        )
        if created:
            user.set_password(DEMO_PASSWORD)
            user.save()
        user.sync_groups()
        return user
