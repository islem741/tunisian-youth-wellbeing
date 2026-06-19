from __future__ import annotations

import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker

from accounts.models import Role
from cases.models import (
    CaseEvent, InterventionPlan, SERSEntry, SERSPolicy, Student, WorkflowState,
)

User = get_user_model()

DEMO_PASSWORD = "demopass123"

SCHOOLS = [
    ("Lycée Pilote Tunis",  "Tunis"),
    ("Collège El Khadra",   "Ariana"),
    ("Lycée Ibn Khaldoun",  "Sousse"),
    ("Collège Hannibal",    "Bizerte"),
]

GRADES = ["7ème", "8ème", "9ème", "1ère Sec", "2ème Sec", "3ème Sec", "4ème Sec"]

FEMALE_NAMES = ["Fatma", "Meriem", "Chiraz", "Amira", "Emna",
                "Rania", "Sarra", "Yasmine", "Ines", "Nour"]
MALE_NAMES   = ["Mohamed", "Ahmed", "Youssef", "Ali", "Amine",
                "Slim", "Khalil", "Anis", "Fares", "Hamza"]
LAST_NAMES   = ["Ben Ali", "Trabelsi", "Rekik", "Ghorbel", "Mzoughi",
                "Gharbi", "Sellami", "Dridi", "Ellouze", "Chaibi"]


class Command(BaseCommand):
    help = "Seed demo data for the Early-Warning platform."

    def add_arguments(self, parser):
        parser.add_argument("--students", type=int, default=40)
        parser.add_argument("--entries",  type=int, default=60)
        parser.add_argument("--seed",     type=int, default=42)

    @transaction.atomic
    def handle(self, *args, **options):
        random.seed(options["seed"])
        fake = Faker()
        Faker.seed(options["seed"])

        # ---- users ----
        operator1  = self._user("operator1",  Role.OPERATOR,
                                "Youssef", "Rekik",
                                school=SCHOOLS[0][0], region=SCHOOLS[0][1])
        operator2  = self._user("operator2",  Role.OPERATOR,
                                "Emna", "Gharbi",
                                school=SCHOOLS[1][0], region=SCHOOLS[1][1])
        supervisor = self._user("supervisor1", Role.SUPERVISOR,
                                "Dr. Sarra", "Mzoughi",
                                school="", region="Tunis")
        admin      = self._user("admin1",      Role.ADMIN,
                                "Zied", "Mansour",
                                school="", region="",
                                is_staff=True, is_superuser=True)

        SERSPolicy.current()  # ensure singleton exists

        # ---- students ----
        existing = Student.objects.count()
        for _ in range(max(0, options["students"] - existing)):
            school, region = random.choice(SCHOOLS)
            gender = random.choice(["F", "M", "O"])
            first  = random.choice(FEMALE_NAMES if gender == "F" else MALE_NAMES)
            Student.objects.create(
                external_id=fake.unique.bothify("STU-####-???"),
                first_name=first,
                last_name=random.choice(LAST_NAMES),
                age=random.randint(12, 18),
                gender=gender,
                grade=random.choice(GRADES),
                school=school,
                region=region,
            )

        students = list(Student.objects.all())

        # ---- SERS entries ----
        for _ in range(options["entries"]):
            student = random.choice(students)
            op      = operator1 if student.school == operator1.school else operator2
            entry   = SERSEntry.objects.create(
                student=student,
                operator=op,
                period_label=fake.bothify("Week ## / 2025"),
                unexcused_absences=random.randint(0, 10),
                grade_drop_points=random.randint(0, 10),
                disciplinary_flags=random.randint(0, 3),
                wellbeing_score=random.randint(1, 10),
                notes=fake.sentence(),
            )
            CaseEvent.objects.create(
                entry=entry, actor=op,
                action=CaseEvent.Action.INTAKE,
                to_state=entry.workflow_state,
                detail=(
                    f"Seed intake. SERS={entry.sers_score} "
                    f"({entry.get_risk_level_display()}). "
                    f"{entry.risk_explanation}"
                ),
            )

        # ---- move some high-risk cases into intervention ----
        high_cases = SERSEntry.objects.filter(
            workflow_state=WorkflowState.ASSESSMENT
        )[:3]
        for case in high_cases:
            case.transition_to(
                WorkflowState.INTERVENTION,
                actor=supervisor,
                reason="Escalated to intervention (demo data).",
            )
            InterventionPlan.objects.create(
                entry=case,
                plan_type=InterventionPlan.PlanType.COUNSELING,
                assigned_to=supervisor,
                notes="Initial counseling session — seeded.",
            )

        # ---- failure-injection demo: one deliberate security event ----
        self.stdout.write(
            "Creating a security-event demo "
            "(operator accessing wrong school)..."
        )
        if high_cases:
            CaseEvent.objects.create(
                entry=high_cases[0], actor=operator2,
                action=CaseEvent.Action.SECURITY,
                detail=(
                    f"Operator {operator2.username} attempted to access "
                    f"entry #{high_cases[0].pk} (student school: "
                    f"{high_cases[0].student.school}, "
                    f"operator school: {operator2.school})."
                ),
            )

        self.stdout.write(self.style.SUCCESS(
            f"\nSeeded successfully (password='{DEMO_PASSWORD}'):\n"
            f"  Users:    operator1, operator2, supervisor1, admin1\n"
            f"  Students: {Student.objects.count()}\n"
            f"  Entries:  {SERSEntry.objects.count()}\n"
            f"  Plans:    {InterventionPlan.objects.count()}\n"
        ))

    def _user(self, username, role, first, last, *,
              school, region, is_staff=False, is_superuser=False):
        user, created = User.objects.get_or_create(
            username=username,
            defaults=dict(
                first_name=first, last_name=last, role=role,
                school=school, region=region,
                is_staff=is_staff, is_superuser=is_superuser,
            ),
        )
        if created:
            user.set_password(DEMO_PASSWORD)
            user.save()
        user.sync_groups()
        return user
