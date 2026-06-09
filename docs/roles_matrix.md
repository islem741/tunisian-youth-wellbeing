# Roles and Permissions Matrix

| Action                                  | Operator | Supervisor | Admin |
|-----------------------------------------|----------|------------|-------|
| Sign in                                 | ✅        | ✅          | ✅     |
| Create student record                   | ✅        | ❌          | ✅     |
| Submit SERS entry (form)                | ✅        | ❌          | ✅     |
| Bulk upload SERS data (CSV)             | ✅        | ❌          | ✅     |
| View own / school cases                 | ✅        | ✅          | ✅     |
| View ALL cases                          | ❌        | ✅          | ✅     |
| Change workflow state                   | ❌        | ✅          | ✅     |
| Create / update intervention plans      | ❌        | ✅          | ✅     |
| Edit SERS weights & thresholds          | ❌        | ❌          | ✅     |
| View program-wide KPI dashboard         | ❌        | ❌          | ✅     |
| Export CSV / PDF reports                | ❌        | ✅          | ✅     |
| Manage users (Django admin)             | ❌        | ❌          | ✅     |

Every denied action is recorded in CaseEvent with action=DENIED.
