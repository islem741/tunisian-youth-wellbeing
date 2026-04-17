"""Shared pytest fixtures for role-based tests."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from accounts.models import Role
from cases.models import RiskPolicy, Student, StressAssessment

User = get_user_model()


@pytest.fixture
def operator(db):
    user = User.objects.create_user(
        username="op",
        password="pw",
        role=Role.OPERATOR,
        school="Lycée Test",
        region="Tunis",
    )
    user.sync_groups()
    return user


@pytest.fixture
def supervisor(db):
    user = User.objects.create_user(
        username="sup",
        password="pw",
        role=Role.SUPERVISOR,
    )
    user.sync_groups()
    return user


@pytest.fixture
def program_admin(db):
    user = User.objects.create_user(
        username="adm",
        password="pw",
        role=Role.ADMIN,
    )
    user.sync_groups()
    return user


@pytest.fixture
def risk_policy(db):
    # Uses threshold = 180 (out of 300) so that we can cross it with
    # three component scores of about 60 in tests.
    policy, _ = RiskPolicy.objects.get_or_create(pk=1, defaults={"threshold": 180})
    policy.threshold = 180
    policy.save()
    return policy


@pytest.fixture
def student(db):
    return Student.objects.create(
        external_id="STU-0001",
        first_name="Amira",
        last_name="Ben Youssef",
        age=15,
        gender="F",
        grade="10",
        school="Lycée Test",
        region="Tunis",
    )


@pytest.fixture
def low_risk_assessment(db, operator, student, risk_policy):
    return StressAssessment.objects.create(
        student=student,
        operator=operator,
        academic_pressure=10,
        social_anxiety=10,
        home_environment=10,
    )


@pytest.fixture
def high_risk_assessment(db, operator, student, risk_policy):
    return StressAssessment.objects.create(
        student=student,
        operator=operator,
        academic_pressure=80,
        social_anxiety=70,
        home_environment=60,
    )
