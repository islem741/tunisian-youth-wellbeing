import io

import pytest
from django.contrib.auth import get_user_model

from accounts.models import Role
from cases.models import SERSEntry, Student
from cases.services import REQUIRED_COLUMNS, ingest_sers_csv

User = get_user_model()


@pytest.fixture
def op(db):
    u = User.objects.create_user(
        username="op_csv", password="pw", role=Role.OPERATOR,
    )
    u.sync_groups()
    return u


@pytest.fixture
def student(db):
    return Student.objects.create(
        external_id="STU-CSV-001",
        first_name="Test", last_name="Student",
        age=14, school="School A", region="Tunis",
    )


def make_csv(*rows, header=None):
    if header is None:
        header = (
            "external_id,unexcused_absences,grade_drop_points,"
            "disciplinary_flags,wellbeing_score,notes"
        )
    lines = [header] + list(rows)
    return io.BytesIO("\n".join(lines).encode())


def test_valid_csv_creates_entries(db, op, student):
    f = make_csv("STU-CSV-001,3,2,0,7,Good week")
    result = ingest_sers_csv(f, operator=op, period_label="Test")
    assert result.created == 1
    assert result.skipped == 0
    assert SERSEntry.objects.filter(student=student).count() == 1


def test_missing_column_header_rejected(db, op):
    # Missing 'wellbeing_score' column
    f = make_csv(
        "STU-CSV-001,3,2,0",
        header="external_id,unexcused_absences,grade_drop_points,disciplinary_flags",
    )
    result = ingest_sers_csv(f, operator=op)
    assert result.has_errors
    assert "wellbeing_score" in result.errors[0]["error"]


def test_unknown_external_id_skipped(db, op):
    f = make_csv("STU-UNKNOWN-999,1,1,0,8,")
    result = ingest_sers_csv(f, operator=op)
    assert result.skipped == 1
    assert "STU-UNKNOWN-999" in result.errors[0]["error"]


def test_non_numeric_value_skipped(db, op, student):
    f = make_csv("STU-CSV-001,NOTANUMBER,2,0,7,")
    result = ingest_sers_csv(f, operator=op)
    assert result.skipped == 1


def test_out_of_range_rejected(db, op, student):
    # wellbeing_score=11 is out of range (max 10)
    f = make_csv("STU-CSV-001,3,2,0,11,")
    result = ingest_sers_csv(f, operator=op)
    assert result.skipped == 1
