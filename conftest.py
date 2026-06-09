"""Shared pytest fixtures for the Tunisian Student Early-Warning Platform."""

from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.template.context import BaseContext

# Python 3.14 compatibility: BaseContext.__copy__ changed in 3.14.
def _patched_base_context_copy(self):
    cls = self.__class__
    duplicate = cls.__new__(cls)
    duplicate.__dict__.update(self.__dict__)
    duplicate.dicts = self.dicts[:]
    return duplicate

BaseContext.__copy__ = _patched_base_context_copy

from accounts.models import Role
from cases.models import SERSEntry, SERSPolicy, Student

User = get_user_model()


# ---------------------------------------------------------------------------
# Role fixtures
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Cases fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sers_policy(db):
    p, _ = SERSPolicy.objects.get_or_create(
        pk=1,
        defaults={
            "absence_weight":    6,
            "grade_drop_weight": 5,
            "behavior_weight":   8,
            "wellbeing_weight":  10,
            "high_threshold":    65,
            "medium_threshold":  40,
        },
    )
    return p


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
def low_risk_entry(db, operator, student, sers_policy):
    return SERSEntry.objects.create(
        student=student,
        operator=operator,
        unexcused_absences=0,
        grade_drop_points=0,
        disciplinary_flags=0,
        wellbeing_score=9,
    )


@pytest.fixture
def high_risk_entry(db, operator, student, sers_policy):
    return SERSEntry.objects.create(
        student=student,
        operator=operator,
        unexcused_absences=8,
        grade_drop_points=8,
        disciplinary_flags=3,
        wellbeing_score=1,
    )
