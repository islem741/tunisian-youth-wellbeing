# Problem Statement

**Population.** Tunisian middle- and high-school students (ages 12–18) across
four partner schools in Tunis, Ariana, Sousse, and Bizerte.

**Problem.** Silent disengagement — rising absences, grade drops, and
unreported distress — often precedes dropout by months. Current workflows
rely on informal paper notes; by the time a school counselor is informed,
the student may already have missed weeks of class.

**Roles.**
- **Operator** (Teacher / Frontline staff): enters attendance, grades,
  behavior notes, well-being check-ins; submits CSV bulk uploads.
- **Supervisor** (School Counselor / Social Worker): reviews flagged students,
  validates scores, creates intervention plans, writes follow-up notes.
- **Admin** (School Director / Program Manager): configures SERS weights and
  thresholds, manages users, monitors audit logs, exports reports.

**Score engine.** A Student Engagement Risk Score (SERS) 0–100 is computed
from four weighted components:

    SERS = (absence_weight × unexcused_absences)
         + (grade_drop_weight × grade_drop_points)
         + (behavior_weight × disciplinary_flags)
         + (wellbeing_weight × low_wellbeing_score)

The score is fully explainable: each case shows a human-readable breakdown.

**Workflow.**

    INTAKE → ASSESSMENT → INTERVENTION → FOLLOW_UP → CLOSED

Every transition is recorded in an immutable audit log.

**Expected value.** Faster detection of high-risk disengagement, auditable
intervention adherence, measurable workflow completion rate.
