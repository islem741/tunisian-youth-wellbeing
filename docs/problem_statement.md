# Problem statement

**Population.** Tunisian middle- and high-school students, ages 11–18,
attending one of four partner schools across Tunis, Ariana, Sousse and
Bizerte.

**Problem.** Early stress and psychosocial distress signals go
unnoticed because current school workflows rely on informal notes and
paper forms. By the time a psychologist is informed, the student may
already have missed classes for weeks.

**Decision maker.** School psychologists (Supervisor role) and the
national program manager (Admin role). Operators (school staff) are
the data-entry users.

**Operational workflow.**
1. Operator creates a `Student` record and submits a `StressAssessment`
   (via form or CSV upload).
2. The rule engine computes the total stress score
   (`academic_pressure + social_anxiety + home_environment`) and
   classifies the case as `LOW`, `MEDIUM` or `HIGH` based on the
   configurable threshold.
3. Supervisor reviews the case on their queue dashboard, transitions
   it to `INTERVENTION` and schedules an appointment.
4. If the appointment is missed, the system logs an automatic
   reminder on the case timeline.
5. Supervisor transitions the case to `FOLLOW_UP` or `CLOSED`.

**Expected value.** Faster detection of high-risk cases, auditable
follow-up adherence, measurable workflow completion rate.

**Validation rule.** A workflow is considered successful when a case
moves from `INTAKE` to `CLOSED` without any `DENIED` audit entry and
with at least one documented intervention step.
