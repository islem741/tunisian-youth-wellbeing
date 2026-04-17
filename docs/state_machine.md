# Workflow state machine

```
          ┌──────────┐
          │  INTAKE  │────────────┐
          └────┬─────┘            │
               │                  │
               ▼                  ▼
        ┌────────────┐        ┌────────┐
        │ ASSESSMENT │──┐     │ CLOSED │
        └─────┬──────┘  │     └────────┘
              │         │       ▲
              ▼         │       │
      ┌─────────────────▼──┐    │
      │ INTERVENTION PLAN. │────┤
      └─────┬──────────────┘    │
            │     ▲             │
            ▼     │             │
       ┌────────────┐           │
       │ FOLLOW_UP  │───────────┘
       └────────────┘
```

Allowed transitions (enforced in `cases.models.ALLOWED_TRANSITIONS`):

| From          | To allowed                          |
|---------------|--------------------------------------|
| Intake        | Assessment, Closed                  |
| Assessment    | Intervention Planning, Closed       |
| Intervention  | Follow-up, Closed                   |
| Follow-up     | Intervention Planning, Closed       |
| Closed        | — (terminal)                        |

Any illegal transition raises a `ValidationError`; the view catches
it and logs a `DENIED` case event for audit.

A newly-created High-Risk assessment is automatically promoted from
`INTAKE` to `ASSESSMENT` so the Supervisor queue picks it up without a
manual step (see `StressAssessment.save`).
