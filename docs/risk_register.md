# Risk Register (Governance)

| # | Category    | Risk                                          | Likelihood | Impact | Mitigation |
|---|-------------|-----------------------------------------------|------------|--------|------------|
| 1 | Data        | Real student data imported by mistake         | Low        | High   | README explicitly warns synthetic-data-only; seed uses Faker; no import path for real data. |
| 2 | Data        | Malformed CSV corrupts the dataset            | Medium     | Medium | `ingest_sers_csv` validates every row; any error rolls back the entire batch atomically. Error table displayed to operator. |
| 3 | Decision    | False positive SERS flags a student unfairly  | Medium     | Medium | Every flag shows component breakdown + threshold; Supervisor can override and the override is logged. |
| 4 | Decision    | False negative misses a disengaged student    | Medium     | High   | Threshold is Admin-configurable; MEDIUM band surfaces borderline cases before they become HIGH. |
| 5 | Operational | Workflow transition skips required state      | Low        | High   | `ALLOWED_TRANSITIONS` dict enforced in `SERSEntry.transition_to()`; illegal transitions raise `ValidationError`. Tested in `test_workflow.py`. |
| 6 | Operational | Operator accesses another school's case       | Low        | High   | `_scoped_entries` scoping + 403 response + `SECURITY` audit event. Tested in `test_permissions.py`. |
| 7 | Privacy     | `notes` exfiltrated via CSV export            | Low        | Medium | `export_cases_csv` omits the `notes` column. |
| 8 | Reliability | Application crash on bad input                | Low        | Medium | `SERSEntry.save()` calls `full_clean()` — raises catchable `ValidationError`, never crashes. |
| 9 | Reliability | Partial CSV import leaves inconsistent state  | Low        | High   | Atomic transaction with `_Rollback` sentinel ensures all-or-nothing import. |
| 10| Security    | SERS policy changed by unprivileged user      | Low        | High   | `@role_required(Role.ADMIN)` on `sers_policy_edit`; non-admins get HTTP 403. |

## Audit trail guarantees

- Every workflow transition creates an immutable `CaseEvent(action=STATE_CHANGE)`.
- Every denied cross-school access creates a `CaseEvent(action=SECURITY)`.
- Every denied role action creates a `CaseEvent(action=DENIED)`.
- All events are visible to Supervisors on the case timeline and to
  Admins on the KPI dashboard.

## Escalation rules

- Any `SECURITY` or `DENIED` event is counted in the Admin KPI dashboard.
- HIGH-risk SERS entries are auto-promoted to Assessment state on creation.
- Supervisors can override any automated risk classification; the override
  is stored as an immutable `STATE_CHANGE` timeline entry.
