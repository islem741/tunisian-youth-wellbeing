# Tunisian Youth Well-being — Stress-level Support Platform

A Django platform that helps Tunisian schools, psychologists and program
managers track student stress levels, flag high-risk cases, and follow
up with intervention appointments. Built as an individual university
exam project for the **Python Web Programming (Django)** course at
SESAME University, 2025–2026.

> All personal data in this repository is **synthetic**. The tool is a
> decision-support aid — **not** a clinical or legal final authority.

## 1. Problem statement (one paragraph)

The platform helps school counselors and program managers monitor
stress levels among **Tunisian middle- and high-school students
(ages 11–18)**. The decision makers — Supervisors (psychologists) and
program Admins — use the tool to detect **high stress cases early**,
trigger a **structured intervention workflow** (assessment → planning
→ follow-up), and **track appointment adherence** with automatic
reminders. The expected value is faster intervention, measurable
follow-up adherence, and an auditable trail of who did what and when.
A workflow is considered successful when it moves from Intake to
Closed with a documented outcome.

## 2. Roles and workflow

Three mandatory roles (stored as both an explicit `User.role` field
and a Django `Group`, so DRF or the admin can rely on either):

| Role        | Can do                                                             |
|-------------|---------------------------------------------------------------------|
| Operator    | Add students, submit stress assessments (form or CSV upload)       |
| Supervisor  | Review cases, set the risk threshold, plan interventions, mark missed appointments |
| Admin       | Monitor KPIs, manage users, adjust policy                          |

Workflow states: **Intake → Assessment → Intervention Planning →
Follow-up → Closed**. Every transition is logged in the case
timeline with author, timestamp and reason (see
`docs/state_machine.md`).

## 3. Quick start

```bash
git clone <this-repo>
cd tunisian-youth-wellbeing

python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python manage.py migrate
python manage.py seed_demo_data          # synthetic users + students + assessments
python manage.py runserver
```

Then open http://127.0.0.1:8000/ and sign in with one of the seeded
accounts (all use the password **`demopass123`**):

| Username       | Role        | Notes                                   |
|----------------|-------------|-----------------------------------------|
| `operator1`    | Operator    | Works for "Lycée Pilote Tunis"          |
| `operator2`    | Operator    | Works for "Collège El Khadra"           |
| `supervisor1`  | Supervisor  | Can edit the risk policy & plan visits  |
| `admin1`       | Admin       | Django superuser, sees KPIs             |

The seed command also creates:

- A configurable **Risk policy** (starts at a total-score threshold of
  75/300; the Supervisor can change it from the dashboard).
- ~40 synthetic **students** spread across four Tunisian schools.
- ~60 **stress assessments** with realistic distributions (some of them
  auto-flagged as High Risk).
- A couple of missed appointments to show the reminder timeline.

## 4. Running the tests (evidence)

```bash
pytest
```

The test suite (see `cases/tests/`) covers:

- **Workflow logic** — a case correctly flips to High Risk when the
  total score crosses the configurable threshold.
- **Failure recovery** — impossible scores (e.g. `-5`, `150`) raise a
  `ValidationError` with a user-facing message instead of crashing;
  CSV uploads with bad rows are rolled back atomically.
- **Role security** — Operators get `403 Forbidden` when they try to
  transition a case, mark an appointment missed, or change the risk
  policy.
- **Appointment reminder** — marking an appointment as missed
  automatically logs a `REMINDER` case event.
- **Dashboard access control** — `/dashboard/admin-kpis/` is only
  reachable by Admins; the Supervisor queue hides cases that are still
  in Intake.

## 5. Scenarios

- **Scenario 1 — Education early warning.** Operator uploads stress
  data (form or CSV at `/cases/upload/`). The rule engine in
  `cases.models.StressAssessment.evaluate_risk` flags cases whose
  total score reaches the configured threshold and writes a
  human-readable explanation on the case, which the Supervisor sees on
  their dashboard (`/dashboard/supervisor/`).

  **Failure injection:** Post an assessment with `academic_pressure=150`
  (or upload a CSV with bad integers). The form re-renders with an
  inline error and nothing is persisted.

- **Scenario 2 — Health / mental-health follow-up.** Supervisor
  schedules appointments from the case detail page. Marking an
  appointment as `Missed` triggers a logged `REMINDER` event on the
  case timeline (the timeline always shows who acted, when, and what
  changed).

  **Failure injection:** An Operator trying to mark the same
  appointment as missed receives a `403 Forbidden`, and the denial is
  logged as a `DENIED` case event for audit.

## 6. Chosen advanced tracks

Per the project statement, at least two advanced tracks are required.
This project implements:

- **Track B — Security & Privacy by design.** Role-based access
  control via a custom `User` model + Django groups, per-view
  decorators (`accounts.permissions.role_required`), synthetic data
  only, CSRF on every form, and audit logging of denied actions on the
  case timeline. See `docs/threat_model.md`.
- **Track D — Observability & Reliability.** Every request gets a
  correlation id (`X-Correlation-ID`) that is attached to structured
  log records (`wellbeing.middleware.CorrelationFilter`); CSV uploads
  use an atomic transaction so a single bad row rolls back the batch;
  the KPI dashboard surfaces "data validation pass rate", "workflow
  completion rate" and "reminders auto-issued" as reliability proxies.

## 7. Project layout

```
wellbeing/          # project (settings, middleware, root urls)
accounts/           # custom User, RBAC helpers, login views
cases/              # domain models, forms, views, tests
dashboard/          # KPI + supervisor queue views
templates/          # base.html + per-app templates (Bootstrap 5)
docs/               # problem statement, roles matrix, state machine,
                    # data dictionary, threat model
```

## 8. Ethics and limitations

- Only synthetic data is used in this repo; real student records must
  never be imported without written consent and an approved data
  governance agreement.
- The stress score is a rough, rule-based proxy. It is intended to
  surface cases for human review, **not** to produce a diagnosis.
- The platform always shows the *reason* behind a flag (component
  breakdown + threshold); Supervisors can override any decision.
- Access is scoped per role, and every denied action is logged so
  abuse is visible in the audit trail.
- See `docs/threat_model.md` and `docs/risk_register.md` for the
  detailed governance notes.
