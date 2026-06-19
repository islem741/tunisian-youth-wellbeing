"""Service layer for SERS computation and CSV ingestion.

Keeping business logic here (not in views or models) means:
- Views stay thin HTTP adapters.
- Logic is unit-testable without HTTP or DB.
- The scoring formula is visible in one place (Track E: explainability).
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field
from typing import Any

from django.db import transaction

from .models import CaseEvent, SERSEntry, SERSPolicy, Student, WorkflowState

logger = logging.getLogger("wellbeing.cases")


# ---------------------------------------------------------------------------
# CSV ingestion
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS = {
    "external_id",
    "unexcused_absences",
    "grade_drop_points",
    "disciplinary_flags",
    "wellbeing_score",
}


@dataclass
class CSVIngestionResult:
    created: int = 0
    skipped: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)


def ingest_sers_csv(
    file_obj,
    *,
    operator,
    period_label: str = "",
) -> CSVIngestionResult:
    """Parse a CSV file and create SERSEntry rows.

    Expected header (order does not matter)::

        external_id, unexcused_absences, grade_drop_points,
        disciplinary_flags, wellbeing_score[, notes][, period_label]

    Returns a :class:`CSVIngestionResult` with per-row error details.

    Failure injection: missing columns, non-numeric values, unknown
    ``external_id``, and out-of-range values are all reported as row
    errors, never as crashes.  The entire upload is rolled back if any
    row fails so the DB never contains a partial batch.
    """
    result = CSVIngestionResult()

    # --- decode ----------------------------------------------------------
    text = file_obj.read()
    if isinstance(text, bytes):
        try:
            text = text.decode("utf-8")
        except UnicodeDecodeError:
            result.errors.append({"row": "—", "error": "File is not valid UTF-8."})
            return result

    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        result.errors.append(
            {"row": "—", "error": "CSV is empty or has no header row."}
        )
        return result

    # Normalise header names to lowercase + stripped for comparison
    normalised_headers = {c.strip().lower() for c in reader.fieldnames}
    missing = REQUIRED_COLUMNS - normalised_headers
    if missing:
        result.errors.append(
            {
                "row": "header",
                "error": f"Missing required columns: {', '.join(sorted(missing))}.",
            }
        )
        return result

    # --- row processing --------------------------------------------------
    try:
        with transaction.atomic():
            for i, row in enumerate(reader, start=2):
                row_num = i
                try:
                    ext_id = row["external_id"].strip()
                    try:
                        student = Student.objects.get(external_id=ext_id)
                    except Student.DoesNotExist:
                        raise ValueError(
                            f"No student with external_id '{ext_id}'."
                        )

                    def _int(key: str) -> int:
                        val = row[key].strip()
                        if not val.lstrip("-").isdigit():
                            raise ValueError(
                                f"'{key}' must be an integer, got '{val}'."
                            )
                        return int(val)

                    entry = SERSEntry(
                        student=student,
                        operator=operator,
                        period_label=row.get(
                            "period_label", period_label
                        ).strip(),
                        unexcused_absences=_int("unexcused_absences"),
                        grade_drop_points=_int("grade_drop_points"),
                        disciplinary_flags=_int("disciplinary_flags"),
                        wellbeing_score=_int("wellbeing_score"),
                        notes=row.get("notes", "").strip(),
                    )
                    entry.save()  # triggers full_clean + risk computation

                    CaseEvent.objects.create(
                        entry=entry,
                        actor=operator,
                        action=CaseEvent.Action.INTAKE,
                        to_state=entry.workflow_state,
                        detail=(
                            f"CSV import (row {row_num}). "
                            f"SERS={entry.sers_score} "
                            f"({entry.get_risk_level_display()})."
                        ),
                    )
                    result.created += 1

                except Exception as exc:
                    result.errors.append({"row": row_num, "error": str(exc)})
                    result.skipped += 1
                    logger.warning("CSV row %d rejected: %s", row_num, exc)

            # Roll back the whole batch if any row failed
            if result.has_errors:
                raise _Rollback()

    except _Rollback:
        # Transaction rolled back; reset created count so caller sees 0
        result.created = 0

    return result


class _Rollback(Exception):
    """Internal sentinel — triggers atomic rollback on any row error."""


# ---------------------------------------------------------------------------
# Auto-reminder helper (called when an intervention due date passes)
# ---------------------------------------------------------------------------

def create_followup_reminder(
    entry: SERSEntry, *, actor=None
) -> CaseEvent:
    """Log an automatic follow-up reminder on a case."""
    return CaseEvent.objects.create(
        entry=entry,
        actor=actor,
        action=CaseEvent.Action.REMINDER,
        detail=(
            f"Automatic reminder: case #{entry.pk} is in "
            f"{entry.get_workflow_state_display()} state and has an "
            f"intervention due date that has passed."
        ),
    )
