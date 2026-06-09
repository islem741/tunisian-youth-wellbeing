# Data Dictionary

## SERSPolicy

| Field              | Type           | Notes                              |
|--------------------|----------------|-------------------------------------|
| absence_weight     | PositiveSmall  | Multiplier for unexcused absences  |
| grade_drop_weight  | PositiveSmall  | Multiplier for grade drop points   |
| behavior_weight    | PositiveSmall  | Multiplier for disciplinary flags  |
| wellbeing_weight   | PositiveSmall  | Multiplier for inverted well-being |
| high_threshold     | PositiveSmall  | SERS ≥ this → HIGH                 |
| medium_threshold   | PositiveSmall  | SERS ≥ this (< high) → MEDIUM      |

## Student

| Field        | Type    | Notes                              |
|--------------|---------|-------------------------------------|
| external_id  | Char    | Synthetic opaque identifier        |
| first_name   | Char    | —                                  |
| last_name    | Char    | —                                  |
| age          | Integer | 10–20                              |
| gender       | Char    | F / M / O                          |
| grade        | Char    | e.g. "9ème", "2ème Sec"            |
| school       | Char    | School name                        |
| region       | Char    | Tunisian governorate               |

## SERSEntry

| Field              | Type           | Notes                              |
|--------------------|----------------|-------------------------------------|
| student            | FK → Student   | —                                  |
| operator           | FK → User      | Who submitted                      |
| period_label       | Char           | e.g. "Week 12 / 2025"              |
| unexcused_absences | PositiveSmall  | 0–30                               |
| grade_drop_points  | PositiveSmall  | 0–20                               |
| disciplinary_flags | PositiveSmall  | 0–10                               |
| wellbeing_score    | PositiveSmall  | 1–10 (1=worst)                     |
| sers_score         | PositiveSmall  | Computed 0–100, set on save        |
| risk_level         | Char           | low / medium / high                |
| risk_explanation   | Text           | Human-readable score breakdown     |
| workflow_state     | Char           | intake/assessment/intervention/... |

## InterventionPlan

| Field       | Type           | Notes                              |
|-------------|----------------|-------------------------------------|
| entry       | FK → SERSEntry | —                                  |
| plan_type   | Char           | parent_meeting/tutoring/etc.       |
| assigned_to | FK → User      | Supervisor responsible             |
| due_date    | Date           | —                                  |
| status      | Char           | pending/active/completed/escalated |

## CaseEvent (audit log — immutable)

| Field      | Type           | Notes                              |
|------------|----------------|-------------------------------------|
| entry      | FK → SERSEntry | —                                  |
| actor      | FK → User      | Null for system events             |
| action     | Char           | intake/state_change/security/etc.  |
| from_state | Char           | Previous workflow state            |
| to_state   | Char           | New workflow state                 |
| detail     | Text           | Human-readable description         |
