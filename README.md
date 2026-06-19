# Tunisian Student Early-Warning & Well-Being Platform

A Django decision-support tool that helps Tunisian middle- and high-school
staff detect **silent disengagement** early — rising absences, grade drops,
and unreported distress — before a student drops out. Built as an individual
university exam project for the **Python Web Programming (Django)** course at
SESAME University, 2025–2026.

> All personal data in this repository is **synthetic**. The tool is a
> decision-support aid — **not** a clinical or legal final authority.

---

## 1. Problem statement

Silent disengagement often precedes dropout by months. Current workflows rely
on informal paper notes; by the time a school counselor is informed, the
student may already have missed weeks of class. This platform gives **Operators**
(teachers / frontline staff) a structured way to submit a **Student Engagement
Risk Score (SERS)** based on four observable components:

    SERS = (absence_weight × unexcused_absences)
         + (grade_drop_weight × grade_drop_points)
         + (behavior_weight × disciplinary_flags)
         + (wellbeing_weight × (10 − wellbeing_score))
         capped at 100

High-risk cases are auto-promoted to Assessment state and appear immediately
on the Supervisor queue. Every scoring decision is fully explained
(component-by-component breakdown) so Supervisors can override it.

See `docs/problem_statement.md` for the complete specification.

---

## 2. Roles and workflow

Three roles (stored as both a `User.role` field and a Django `Group`):

| Role       | Key actions                                                          |
|------------|----------------------------------------------------------------------|
| Operator   | Create students, submit SERS entries (form or CSV), view own cases  |
| Supervisor | Review flagged cases, create intervention plans, transition workflow |
| Admin      | Configure SERS weights/thresholds, manage users, view KPI dashboard |

Workflow: **Intake → Assessment → Intervention Planning → Follow-up → Closed**

Every transition is recorded in an immutable `CaseEvent` audit log with
actor, timestamp, and reason. See `docs/state_machine.md`.

---

## 3. Quick start

```bash
git clone <this-repo>
cd tunisian-youth-wellbeing

# Windows
python -m venv .venv
.venv\Scripts\Activate.ps1

# macOS / Linux
python -m venv .venv && source .venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo_data
python manage.py runserver
```

Open **http://127.0.0.1:8000/** and sign in (password **`demopass123`** for all):

| Username     | Role       | School / Notes                        |
|--------------|------------|---------------------------------------|
| `operator1`  | Operator   | Lycée Pilote Tunis                    |
| `operator2`  | Operator   | Collège El Khadra                     |
| `supervisor1`| Supervisor | Dr. Sarra Mzoughi — sees case queue  |
| `admin1`     | Admin      | Zied Mansour — KPI dashboard, policy |

The seed command creates:
- A **SERSPolicy** singleton (weights and thresholds, configurable by Admin).
- **40 synthetic students** across four Tunisian schools.
- **60 SERS entries** with realistic score distributions (some auto-flagged HIGH).
- **3 intervention plans** on the highest-risk cases.
- **1 deliberate security event** (operator2 accessing wrong school) visible on
  the Admin KPI dashboard.

---

## 4. Running the tests

```bash
pytest
```

The test suite (`cases/tests/`) covers:

| File | What it tests |
|---|---|
| `test_sers_scoring.py` | SERS formula, risk classification, invalid value rejection, auto-promotion |
| `test_csv_ingestion.py` | Valid upload, missing columns, unknown student, non-numeric values, out-of-range |
| `test_permissions.py` | Operator blocked from wrong school (403 + security event logged), SERS policy locked to Admin, Supervisor can view any case |
| `test_workflow.py` | Valid transitions, illegal transition raises, audit event logged, intervention plan completion |

---

## 5. Scenarios and failure injection

### Scenario 1 — Education early warning (SERS flagging)

**Happy path:**
1. Log in as `operator1`.
2. Go to **Cases → New Entry** (`/cases/entry/new/`).
3. Submit realistic scores. If SERS ≥ 65, the case is auto-promoted to
   Assessment and appears on the Supervisor queue immediately.
4. The case detail page shows the full component breakdown and explanation.

**Failure injection — bad form values:**
Submit `wellbeing_score = 11` (out of range). The form re-renders with an
inline validation error. Nothing is persisted. The `ValidationError` is raised
in `SERSEntry.clean()`.

**Failure injection — malformed CSV:**
Go to **Cases → Upload CSV** (`/cases/entry/upload/`). Upload a file missing
the `wellbeing_score` column. The error table is displayed showing the exact
column name that is missing. The entire batch is rolled back atomically
(`cases/services.py` uses `transaction.atomic` + `_Rollback` sentinel).

### Scenario 2 — Role-based access control (security)

**Happy path:**
1. Log in as `supervisor1`.
2. Go to the Supervisor Queue (`/dashboard/supervisor/`).
3. Open a HIGH-risk case, create an Intervention Plan, transition the
   workflow state.

**Failure injection — operator accessing wrong school:**
`operator2` (school: Collège El Khadra) attempting to access a case belonging
to a student at Lycée Pilote Tunis receives **HTTP 403 Forbidden**. The denial
is recorded as a `CaseEvent` with `action=SECURITY`. This event is visible on
the Admin KPI dashboard under "Security Events". The test
`test_operator_cannot_access_other_school_case` in `cases/tests/test_permissions.py`
verifies this automatically.

**Failure injection — operator trying to edit SERS policy:**
`operator1` accessing `/cases/policy/` receives **HTTP 403 Forbidden** immediately
(enforced by `@role_required(Role.ADMIN)` in `cases/views.py`).

---

## 6. Advanced tracks implemented

Per the project statement, at least two advanced tracks are required.

### Track B — Security & Privacy by design

- Custom `User` model with three roles (`accounts/models.py`).
- Django `Groups` kept in sync via `User.sync_groups()` for built-in admin
  compatibility.
- `role_required` decorator (`accounts/permissions.py`) returns HTTP 403 for
  wrong-role access; unauthenticated users are redirected to login.
- Operators are scoped to their own submissions + their school's students
  (`cases/views._scoped_entries`).
- Every denied cross-school access is logged as a `CaseEvent(action=SECURITY)`.
- CSRF tokens on every form. Synthetic data only.
- See `docs/threat_model.md`.

### Track D — Observability & Reliability

- Every HTTP request receives a `X-Correlation-ID` header attached to all
  structured log records (`wellbeing/middleware.py` — `CorrelationFilter`).
- CSV uploads use `transaction.atomic` + a `_Rollback` sentinel so a single
  bad row rolls back the entire batch — no partial imports.
- KPI dashboard (`/dashboard/admin-kpis/`) surfaces:
  - Workflow completion rate (% closed)
  - Intervention completion rate
  - Data validation pass rate (intakes vs. denied actions)
  - Security event count
  - Average SERS score
- See `docs/risk_register.md`.

---

## 7. Project layout

```
wellbeing/          # project (settings, middleware, root URLs)
accounts/           # custom User model, RBAC helpers, login views
cases/              # SERS models, forms, views, services, tests
dashboard/          # KPI dashboard + supervisor queue views
templates/          # base.html + per-app templates (Bootstrap 5)
docs/               # problem statement, roles matrix, state machine,
                    #   data dictionary, threat model, risk register
```

---

## 8. Ethics and limitations

- Only synthetic data is used; real student records must never be imported
  without written consent and an approved data-governance agreement.
- The SERS is a rule-based proxy. It surfaces cases for human review — it is
  **not** a diagnostic tool.
- The platform always shows the *reason* behind a flag (component breakdown +
  threshold); Supervisors can override any automated decision.
- All denied actions are logged so abuse is visible in the audit trail.
- See `docs/threat_model.md` and `docs/risk_register.md` for governance notes.

---

## 9. Datasets

### What is and is not included

| Item | Included in repo? | How to obtain |
|---|---|---|
| `db.sqlite3` | ❌ No | Run `python manage.py seed_demo_data` |
| Student records | ❌ No real data | Generated by `seed_demo_data` |
| `evidence/sample_upload.csv` | ✅ Yes | See `evidence/README.md` |

### What `seed_demo_data` creates

All data is **synthetic**, generated by the [Faker](https://faker.readthedocs.io/)
library with a fixed seed (`seed=42`) for full reproducibility. Running the
command twice on an empty database produces identical records.

- **4 demo users** — `operator1`, `operator2`, `supervisor1`, `admin1`
  (password `demopass123` for all).
- **~40 students** with Tunisian names, spread across four partner schools
  (Tunis, Ariana, Sousse, Bizerte).
- **~60 SERS entries** with random but realistic component values; some
  entries automatically score ≥ 65 and are promoted to the Assessment
  workflow state.
- **3 intervention plans** attached to the three highest-risk cases.
- **1 deliberate security event** — `operator2` logged as having attempted
  to access a case from `operator1`'s school, visible on the Admin
  KPI dashboard.

### Sample CSV (`evidence/sample_upload.csv`)

Contains **5 valid rows** + **1 bad row** (`wellbeing_score=11`, max is 10).

Upload it at `/cases/entry/upload/` as `operator1` to demonstrate:

- ✅ Happy path: 5 entries would be imported.
- ❌ Failure injection: the bad row triggers `ValidationError` in
  `SERSEntry.clean()`, the error table is rendered, and the entire batch
  is rolled back atomically — zero entries are persisted.

> **Note:** the `external_id` values in the CSV (`STU-0001-TUN` …
> `STU-0005-TUN`) must match students that exist in the database. Run
> `python manage.py seed_demo_data` first, then re-export a student's
> `external_id` from `/cases/` or the Django admin before uploading.
> Alternatively, create five students manually at `/cases/student/new/`
> with those exact IDs.

---

## 10. Submission checklist

Based on the exam PDF §22 Student Quick Checklist.

- [x] **Problem statement and stakeholders** —
  `docs/problem_statement.md` · Population (Tunisian students 12–18),
  problem (silent disengagement), decision makers (Operator / Supervisor /
  Admin), expected value (faster detection, auditable adherence).

- [x] **Scenario 1 implemented + failure evidence** —
  `cases/views.entry_upload_csv` + `cases/services.ingest_sers_csv`.
  Test: `cases/tests/test_csv_ingestion.py` (5 tests, all pass).
  Evidence: `docs/failure_injection_evidence.md` Case 1.

- [x] **Scenario 2 implemented + failure evidence** —
  `cases/views.case_detail` scope check (lines 82–95).
  Tests: `cases/tests/test_permissions.py` (5 tests, all pass).
  Evidence: `docs/failure_injection_evidence.md` Case 2.

- [x] **At least 2 advanced tracks** —
  `docs/advanced_tracks.md` documents:
  - Track A — Service layer (`cases/services.py`) + ORM `select_related`.
  - Track B — RBAC (`accounts/permissions.py`) + audit logging.
  - Track D — Correlation-ID middleware + atomic CSV + KPI dashboard.
  - Track F (partial) — RAG retriever (`support/rag/retriever.py`).

- [x] **Roles and permissions validated by tests** —
  `cases/tests/test_permissions.py`:
  `test_operator_cannot_access_other_school_case`,
  `test_operator_cannot_view_sers_policy`,
  `test_supervisor_cannot_create_entry`,
  `test_supervisor_can_view_case`,
  `test_security_event_logged_on_unauthorized_access`.

- [x] **Dashboard and reports operational** —
  `/dashboard/admin-kpis/` (workflow completion, validation pass rate,
  security events, avg SERS score, by-region/school breakdown).
  `/cases/export.csv` (Supervisor / Admin CSV export).
  Tests: `cases/tests/test_dashboard.py` (5 tests, all pass).

- [x] **README and setup commands verified** —
  Section 3 Quick Start above. Commands tested on a clean Windows +
  Python 3.14 environment:
  ```
  pip install -r requirements.txt
  python manage.py migrate
  python manage.py seed_demo_data
  python manage.py runserver
  ```

- [x] **Full test suite green** —
  ```
  pytest          # 39 passed, 0 failed
  ```
  Covers SERS scoring, CSV ingestion, permissions, workflow transitions,
  dashboard views, and RAG retrieval.

- [x] **Ethics and limitations** —
  Section 8 of this README + `docs/risk_register.md` (10 risks with
  mitigations) + `docs/threat_model.md` (8 abuse cases with mitigations).
  Synthetic data only; rule-based proxy (not a diagnostic); Supervisor
  override always available; scope limited to demo data.

- [x] **Individual work policy respected** —
  This project was built individually. All code in this repository was
  written by the student. AI tools were used for assistance and pair
  programming; all design decisions, architecture choices, and final
  implementations are the student's own work.
