# Workflow State Machine

```
┌──────────┐
│  INTAKE  │────────────────┐
└────┬─────┘                │
     │                      ▼
     ▼                 ┌────────┐
┌────────────┐           │ CLOSED │
│ ASSESSMENT │──────────▶│        │
└─────┬──────┘           └────────┘
      │                      ▲
      ▼                      │
┌──────────────────┐           │
│   INTERVENTION   │───────────┤
└────────┬─────────┘           │
         │       ▲             │
         ▼       │             │
    ┌───────────┐│             │
    │ FOLLOW_UP ├┘             │
    └───────────┴──────────────┘
```

Allowed transitions (enforced in `cases.models.ALLOWED_TRANSITIONS`):

| From         | To allowed                        |
|--------------|-----------------------------------|
| INTAKE       | ASSESSMENT, CLOSED                |
| ASSESSMENT   | INTERVENTION, CLOSED              |
| INTERVENTION | FOLLOW_UP, CLOSED                 |
| FOLLOW_UP    | INTERVENTION, CLOSED              |
| CLOSED       | — (terminal)                      |

A newly created HIGH-risk SERS entry is auto-promoted INTAKE → ASSESSMENT.
