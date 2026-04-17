# Risk register (governance)

| # | Category      | Risk                                         | Likelihood | Impact | Mitigation |
|---|---------------|----------------------------------------------|------------|--------|------------|
| 1 | Data          | Real data imported by mistake                | Low        | High   | README warns that only synthetic data is allowed; seed command uses Faker. |
| 2 | Data          | Low-quality CSV uploads corrupt stats        | Med        | Med    | CSV upload is validated row-by-row; any error rolls back the whole batch. |
| 3 | Decision      | False positive flags a student unfairly      | Med        | Med    | Every flag includes a component breakdown explanation; Supervisor can override. |
| 4 | Decision      | False negative misses a stressed student     | Med        | High   | Threshold is configurable; medium-risk band surfaces borderline cases. |
| 5 | Operational   | Silent workflow failure (reminder lost)      | Low        | High   | Reminders are stored as `CaseEvent` rows, visible on the case timeline. |
| 6 | Operational   | Unauthorized action                          | Low        | High   | Role decorators + audit log (`DENIED` events). |
| 7 | Privacy       | Exfiltration of `notes` through CSV export   | Low        | Med    | Export omits free-text `notes`. |
| 8 | Reliability   | App crashes on bad input                     | Low        | Med    | `full_clean()` in `save()` raises catchable `ValidationError`. |

## Escalation rules

- Any `DENIED` event creates a trail visible to Admin through the KPI
  dashboard.
- Missed appointments automatically queue a reminder and add a visible
  row on the Supervisor queue.
- The Supervisor can override any automated classification; the
  override is stored as an immutable timeline entry.
