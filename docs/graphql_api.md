# GraphQL API Documentation

Tunisian Student Early-Warning & Well-Being Platform  
Endpoint: `POST /graphql/`  
Interactive playground (GraphiQL): `http://127.0.0.1:8000/graphql/` *(requires DEBUG=True)*

---

## 1. Schema Design

The schema is built with **Strawberry GraphQL** and exposes all existing domain
entities through read-only types and write mutations.  No business logic was
duplicated — every mutation delegates to the same model methods and service
functions used by the HTML views.

### Output Types

| Type | Source model |
|---|---|
| `UserType` | `accounts.models.User` |
| `StudentType` | `cases.models.Student` |
| `SERSEntryType` | `cases.models.SERSEntry` |
| `CaseEventType` | `cases.models.CaseEvent` |
| `InterventionPlanType` | `cases.models.InterventionPlan` |
| `SERSPolicyType` | `cases.models.SERSPolicy` |
| `DashboardMetricsType` | computed in `dashboard/views.admin_kpis` |
| `RegionBreakdownType` | aggregation over `SERSEntry` |
| `SchoolBreakdownType` | aggregation over `SERSEntry` |

### Filter Inputs

`SERSEntryFilterInput`:  `riskLevel`, `workflowState`, `school`, `region`,
`operatorId`, `createdAfter`, `createdBefore`

`StudentFilterInput`: `school`, `region`, `gender`, `grade`

---

## 2. Security Model

Authentication uses Django **session cookies** (same as the rest of the app).
The GraphQL layer never receives raw passwords.

All permission checks are enforced by Strawberry `BasePermission` classes in
`gql/permissions.py`. A failed check raises a `StrawberryGraphQLError` and the
field resolves to `null` with an error entry in the response payload — the HTTP
status is always **200** (standard GraphQL behaviour).

| Permission class | Allowed roles | Applied to |
|---|---|---|
| `IsOperatorOrAbove` | operator, supervisor, admin | All queries |
| `IsSupervisorOrAbove` | supervisor, admin | transitionCase, createInterventionPlan, completeInterventionPlan |
| `IsAdmin` | admin | dashboardMetrics, updateSersPolicy |

**Scoping**: the `sersEntries`, `sersEntry`, `caseEvents`, `interventionPlans`,
and `students` queries all apply the same school-scoping logic as the HTML
views — Operators only see their school's data.

---

## 3. Queries (12 total)

### `me` — return the current user

```graphql
{ me { username role school fullName } }
```

**Response:**
```json
{ "data": { "me": { "username": "operator1", "role": "operator",
    "school": "Lycée Pilote Tunis", "fullName": "Youssef Rekik" } } }
```

---

### `students` — list students with optional filtering

```graphql
{
  students(filter: { school: "Lycée Pilote Tunis" }) {
    externalId displayName age grade
  }
}
```

---

### `student` — single student by external ID

```graphql
{ student(externalId: "STU-0012-TUN") { displayName school region } }
```

---

### `sersEntries` — list SERS entries with filtering

```graphql
{
  sersEntries(filter: { riskLevel: "high", workflowState: "assessment" }) {
    id sersScore riskLevel riskExplanation workflowState
    student { displayName school }
    operator { username }
  }
}
```

**Response (excerpt):**
```json
{
  "data": {
    "sersEntries": [
      { "id": "14", "sersScore": 89, "riskLevel": "high",
        "workflowState": "assessment",
        "student": { "displayName": "Ahmed Ghorbel", "school": "Lycée Pilote Tunis" },
        "operator": { "username": "operator1" } }
    ]
  }
}
```

---

### `sersEntry` — single entry by id

```graphql
{
  sersEntry(id: "14") {
    id sersScore riskExplanation
    events { action detail createdAt }
    interventions { planType status dueDate }
  }
}
```

---

### `caseEvents` — audit trail for an entry

```graphql
{ caseEvents(entryId: "14") { action fromState toState detail createdAt actor { username } } }
```

---

### `interventionPlans` — plans for an entry

```graphql
{ interventionPlans(entryId: "14") { planType status dueDate assignedTo { fullName } } }
```

---

### `sersPolicy` — current scoring weights

```graphql
{ sersPolicy { absenceWeight gradeDropWeight behaviorWeight wellbeingWeight highThreshold mediumThreshold } }
```

---

### `dashboardMetrics` *(Admin only)*

```graphql
{
  dashboardMetrics {
    totalEntries closedEntries completionRate
    validationPassRate securityEventCount avgSersScore
    planTotal planCompleted planCompletionRate
    highRiskCount mediumRiskCount lowRiskCount
  }
}
```

---

### `regionBreakdown` *(Supervisor / Admin)*

```graphql
{ regionBreakdown { region count } }
```

---

### `schoolBreakdown` *(Supervisor / Admin)*

```graphql
{ schoolBreakdown { school count } }
```

---

### `supervisorQueue` *(Supervisor / Admin)*

```graphql
{
  supervisorQueue {
    id sersScore riskLevel workflowState
    student { displayName }
  }
}
```

---

## 4. Mutations (6 total)

### `createStudent` *(Operator / Admin)*

```graphql
mutation {
  createStudent(data: {
    externalId: "STU-NEW-001"
    firstName: "Nour"
    lastName: "Gharbi"
    age: 14
    gender: "F"
    school: "Lycée Ibn Khaldoun"
    region: "Sousse"
  }) {
    ... on StudentType { externalId displayName }
    ... on MutationError { message field }
  }
}
```

---

### `createSersEntry` *(Operator / Admin)*

Delegates to `SERSEntry.save()` which calls `full_clean()` and computes the
SERS score automatically. HIGH-risk entries are auto-promoted to Assessment.

```graphql
mutation {
  createSersEntry(data: {
    studentExternalId: "STU-NEW-001"
    unexcusedAbsences: 7
    gradeDropPoints: 6
    disciplinaryFlags: 2
    wellbeingScore: 2
    periodLabel: "June 2026"
    notes: "Increased absences this month."
  }) {
    ... on SERSEntryType { id sersScore riskLevel workflowState riskExplanation }
    ... on MutationError { message }
  }
}
```

**Success response:**
```json
{
  "data": {
    "createSersEntry": {
      "id": "75", "sersScore": 94, "riskLevel": "high",
      "workflowState": "assessment",
      "riskExplanation": "Absences 7×6=42 pts; grade drop 6×5=30 pts; ..."
    }
  }
}
```

**Validation failure (wellbeing_score=11):**
```json
{
  "data": {
    "createSersEntry": {
      "message": "wellbeing_score: Must be between 1 and 10."
    }
  }
}
```

---

### `transitionCase` *(Supervisor / Admin)*

Delegates to `SERSEntry.transition_to()` which enforces the state machine.

```graphql
mutation {
  transitionCase(data: {
    entryId: "75"
    toState: "intervention"
    reason: "Counselor assigned — scheduled session on 2026-06-15."
  }) {
    ... on SERSEntryType { id workflowState }
    ... on MutationError { message }
  }
}
```

**Illegal transition response:**
```json
{
  "data": {
    "transitionCase": {
      "message": "Illegal transition intake → intervention."
    }
  }
}
```

---

### `createInterventionPlan` *(Supervisor / Admin)*

```graphql
mutation {
  createInterventionPlan(data: {
    entryId: "75"
    planType: "counseling"
    assignedToId: "3"
    dueDate: "2026-07-01"
    notes: "Three weekly sessions."
  }) {
    ... on InterventionPlanType { id planType status dueDate }
    ... on MutationError { message }
  }
}
```

---

### `completeInterventionPlan` *(Supervisor / Admin)*

Delegates to `InterventionPlan.mark_completed()`.

```graphql
mutation {
  completeInterventionPlan(data: { planId: "5" }) {
    ... on InterventionPlanType { id status }
    ... on MutationError { message }
  }
}
```

---

### `updateSersPolicy` *(Admin only)*

Partial update — only supply the fields you want to change.
Validates that `mediumThreshold < highThreshold`.

```graphql
mutation {
  updateSersPolicy(data: {
    absenceWeight: 7
    highThreshold: 70
  }) {
    ... on SERSPolicyType { absenceWeight highThreshold mediumThreshold }
    ... on MutationError { message }
  }
}
```

---

## 5. Error Handling

All errors are returned in the standard GraphQL payload — HTTP status is
always 200. Two layers of error reporting are used:

**Permission errors** (via `StrawberryGraphQLError`):
```json
{
  "data": null,
  "errors": [
    { "message": "You must be a Supervisor or Admin to perform this action.",
      "locations": [{ "line": 3, "column": 11 }],
      "path": ["transitionCase"] }
  ]
}
```

**Validation errors** (via `MutationError` union type — NOT in the `errors` array):
```json
{
  "data": {
    "createSersEntry": {
      "message": "wellbeing_score: Must be between 1 and 10."
    }
  }
}
```

This distinction is intentional: permission failures crash the field because
the client must not receive partial data; validation failures return a typed
result so the client can display them inline.

---

## 6. Files Created / Modified

### New files

| File | Purpose |
|---|---|
| `gql/__init__.py` | Package marker |
| `gql/permissions.py` | Strawberry `BasePermission` classes (4) |
| `gql/types.py` | Output types + mapper helpers |
| `gql/inputs.py` | Input types for mutations and filters |
| `gql/queries.py` | 12 query resolvers |
| `gql/mutations.py` | 6 mutation resolvers |
| `gql/schema.py` | Schema assembly + `graphql_view` |
| `gql/tests/__init__.py` | Test package marker |
| `gql/tests/test_graphql.py` | 23 automated tests |
| `docs/graphql_api.md` | This document |

### Modified files

| File | Change |
|---|---|
| `wellbeing/urls.py` | Added `path("graphql/", graphql_view)` |
| `wellbeing/settings.py` | Added `"strawberry.django"` to `INSTALLED_APPS` |
| `requirements.txt` | Added `strawberry-graphql[django]>=0.250.0` and `python-pptx>=1.0` |

---

## 7. Test Commands

```bash
# GraphQL tests only
pytest gql/tests/test_graphql.py -v

# Full suite (62 tests)
pytest

# With coverage
pytest gql/tests/test_graphql.py -v --cov=gql
```

---

## 8. Advanced Track Requirement Satisfied

This implementation satisfies the university exam requirement:

> *"Optional GraphQL endpoint with explicit schema design and resolver authorization."*

Specifically:

- **Explicit schema design** — full SDL generated via `schema.as_str()`, all types documented above.
- **Resolver authorization** — every resolver carries `permission_classes=[...]` with one of the four permission classes. Unauthorized access returns a structured error, never an HTTP 4xx.
- **Integration, not a toy** — resolvers reuse `SERSEntry.save()`, `entry.transition_to()`, `InterventionPlan.mark_completed()`, `SERSPolicy.current()`, `_scoped_entries()`, and `dashboard/views.admin_kpis` logic. No business rules were copied.
- **Track B (Security & Privacy by design)** — RBAC enforced at GraphQL layer using the same role model as the HTML views.
- **Track D (Observability & Reliability)** — all mutations write `CaseEvent` audit records through the same service layer, keeping the audit trail complete regardless of which interface (HTML or GraphQL) was used.
