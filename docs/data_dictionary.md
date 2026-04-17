# Data dictionary

All values in the bundled database are **synthetic**, generated with
`Faker` in `accounts/management/commands/seed_demo_data.py`.

## `accounts.User`

| Field       | Type      | Notes                                         |
|-------------|-----------|-----------------------------------------------|
| username    | CharField | login, unique                                 |
| role        | CharField | one of `operator`, `supervisor`, `admin`      |
| school      | CharField | optional, scopes Operator visibility          |
| region      | CharField | optional administrative region                |

## `cases.Student`

| Field       | Type      | Range / notes                                 |
|-------------|-----------|-----------------------------------------------|
| external_id | CharField | synthetic opaque id, unique                   |
| first_name  | CharField | synthetic                                     |
| last_name   | CharField | synthetic                                     |
| age         | int       | 6–25, validated                               |
| gender      | CharField | `F` / `M` / `O`                               |
| grade       | CharField | free text                                     |
| school      | CharField | one of the four partner schools               |
| region      | CharField | Tunis, Ariana, Sousse, Bizerte                |

## `cases.StressAssessment`

| Field              | Type                         | Range / notes |
|--------------------|------------------------------|---------------|
| student            | FK → Student                 |               |
| operator           | FK → User (Operator)         |               |
| academic_pressure  | PositiveSmallIntegerField    | 0–100         |
| social_anxiety     | PositiveSmallIntegerField    | 0–100         |
| home_environment   | PositiveSmallIntegerField    | 0–100         |
| total_score        | computed                     | 0–300         |
| workflow_state     | CharField                    | see state machine |
| risk_level         | CharField                    | `low`/`medium`/`high` |
| risk_explanation   | TextField                    | human-readable reason |

## `cases.RiskPolicy`

Singleton row with the current High-Risk threshold (integer, 1–300).
Default = 75 out of 300 — adjustable by any Supervisor or Admin.

## `cases.Appointment`

| Field          | Type      | Notes                                   |
|----------------|-----------|-----------------------------------------|
| assessment     | FK        |                                         |
| scheduled_for  | DateTime  |                                         |
| scheduled_by   | FK → User |                                         |
| status         | CharField | `scheduled` / `completed` / `missed` / `cancelled` |
| notes          | TextField |                                         |

## `cases.CaseEvent`

Immutable audit entries. Actions: `intake`, `state_change`,
`appointment`, `reminder`, `note`, `denied`. Used to render the case
timeline and to compute the "Data validation pass rate" KPI.
