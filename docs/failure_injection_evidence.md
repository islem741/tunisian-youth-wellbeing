# Failure Injection Evidence

This document records the two required failure-injection cases for the
Tunisian Student Early-Warning & Well-Being Platform exam project.
Each case shows the input, the expected system behaviour, the automated
test that verifies it, and the exact lines of code that form the guard.

---

## Case 1 — CSV Upload with Out-of-Range Data (Scenario 1)

### Summary table

| Property          | Detail |
|-------------------|--------|
| **Scenario**      | Scenario 1 — Education Early Warning (SERS flagging) |
| **Test file**     | `cases/tests/test_csv_ingestion.py` |
| **Test name**     | `test_out_of_range_rejected` |
| **Actor**         | Operator (school staff submitting bulk data) |
| **Injection**     | CSV row with `wellbeing_score=11` (valid range is 1–10) |
| **Expected outcome** | `CSVIngestionResult.skipped == 1`, zero `SERSEntry` rows created, entire batch rolled back |
| **Primary guard** | `SERSEntry.clean()` — `cases/models.py`, line 228 |
| **Rollback guard**| `_Rollback` sentinel — `cases/services.py`, line 155 |
| **HTTP behaviour**| Form re-renders with per-row error table; no crash; no partial import |

### Narrative

An Operator uploads a CSV file containing a row where `wellbeing_score` is
set to `11`. The valid range for this field is `1–10` (enforced by
`MinValueValidator(1)` and `MaxValueValidator(10)` on the model field, and
double-checked in `SERSEntry.clean()`).

The call chain is:

```
ingest_sers_csv()                  # cases/services.py
  └─ entry.save()                  # line 133 — triggers full_clean + risk computation
       └─ SERSEntry.save()         # cases/models.py line 265
            └─ self.full_clean()   # line 265 — calls clean() on all fields
                 └─ SERSEntry.clean()  # line 228 — raises ValidationError
                      {"wellbeing_score": "Must be between 1 and 10."}
  └─ except Exception as exc:      # services.py line 149
       result.errors.append(...)   # line 150
       result.skipped += 1         # line 150
  └─ if result.has_errors:         # line 155
       raise _Rollback()           # line 155 — triggers atomic rollback
except _Rollback:                  # line 157
  result.created = 0               # line 160 — caller sees truthful count
```

Because the entire loop runs inside `with transaction.atomic()`, raising
`_Rollback` rolls back every `SERSEntry` row that was created earlier in the
same batch — ensuring no partial import reaches the database.

The upload template (`templates/cases/entry_upload.html`) renders the
`result.errors` list as a table, showing the row number and the exact
validation message. The operator sees a clear, human-readable explanation
rather than a 500 error.

### Test assertion

```python
# cases/tests/test_csv_ingestion.py — test_out_of_range_rejected
def test_out_of_range_rejected(db, op, student):
    f = make_csv("STU-CSV-001,3,2,0,11,")   # wellbeing_score=11 is invalid
    result = ingest_sers_csv(f, operator=op)
    assert result.skipped == 1              # row was rejected
    # implicitly: result.created == 0 and no SERSEntry in DB
```

---

## Case 2 — Operator Accessing Another School's Case (Scenario 2)

### Summary table

| Property          | Detail |
|-------------------|--------|
| **Scenario**      | Scenario 2 — Role-Based Access Control |
| **Test file**     | `cases/tests/test_permissions.py` |
| **Test name**     | `test_operator_cannot_access_other_school_case` |
| **Actor**         | `other_operator` — an Operator whose `school` is "School B" |
| **Injection**     | HTTP `GET /cases/{pk}/` for a case whose student belongs to "School A" |
| **Expected outcome** | HTTP 403 Forbidden; `CaseEvent(action=SECURITY)` written to the audit log |
| **Primary guard** | `case_detail()` scope check — `cases/views.py`, lines 82–95 |
| **Audit guard**   | `CaseEvent.objects.create(action=SECURITY)` — `cases/views.py`, line 89 |
| **HTTP behaviour**| Django renders the standard 403 Forbidden page; no data exposed |

### Narrative

`other_operator` works at "School B". A `SERSEntry` exists for a student
enrolled at "School A", submitted by `operator` (School A staff). When
`other_operator` tries to access the case detail page, the view first fetches
the entry from the full queryset (to allow logging), then checks scope:

```
case_detail(request, pk)           # cases/views.py line 74
  └─ full_qs = SERSEntry.objects…  # line 78 — unrestricted fetch for logging
  └─ entry = get_object_or_404(…)  # line 80 — 404 only if case doesn't exist at all
  └─ if request.user.is_operator:  # line 82
       in_scope = (
           entry.operator == request.user          # own submission?
           or entry.student.school == user.school  # same school?
       )                            # line 83–86
       if not in_scope:             # line 87
           CaseEvent.objects.create(
               action=CaseEvent.Action.SECURITY,   # line 89 — immutable audit entry
               detail="Operator op_other attempted to view entry #1 …"
           )
           raise PermissionDenied(…)               # line 95 → HTTP 403
```

The key design decision is that the entry is fetched *before* the scope check,
not filtered out by the queryset. This ensures the audit event can always be
written — even if the operator could not normally see the entry. If the scope
check used `get_object_or_404(_scoped_entries(user), pk=pk)`, a cross-school
attempt would return 404 with no audit trail.

The `CaseEvent(action=SECURITY)` is immutable, visible to Supervisors on the
case timeline and counted by the Admin KPI dashboard under "Security Events".

### Test assertions

```python
# cases/tests/test_permissions.py

def test_operator_cannot_access_other_school_case(db, other_operator, entry, client):
    client.force_login(other_operator)
    response = client.get(reverse("cases:detail", args=[entry.pk]))
    assert response.status_code == 403          # access is blocked

def test_security_event_logged_on_unauthorized_access(db, other_operator, entry, client):
    client.force_login(other_operator)
    client.get(reverse("cases:detail", args=[entry.pk]))
    assert CaseEvent.objects.filter(            # audit trail created
        action=CaseEvent.Action.SECURITY,
        entry=entry,
    ).exists()
```

---

## Running the tests

```bash
pytest cases/tests/test_csv_ingestion.py::test_out_of_range_rejected -v
pytest cases/tests/test_permissions.py::test_operator_cannot_access_other_school_case -v
pytest cases/tests/test_permissions.py::test_security_event_logged_on_unauthorized_access -v
```

All three pass on a clean database with `pytest cases/tests/ -v`.
