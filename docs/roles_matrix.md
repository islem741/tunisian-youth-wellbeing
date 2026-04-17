# Roles and permissions matrix

| Action                                   | Operator | Supervisor | Admin |
|------------------------------------------|----------|------------|-------|
| Sign in                                  | ✅        | ✅          | ✅     |
| Create student                           | ✅        | ❌          | ✅     |
| Submit stress assessment (form)          | ✅        | ❌          | ✅     |
| Bulk upload assessments (CSV)            | ✅        | ❌          | ✅     |
| View own / school cases                  | ✅        | ✅          | ✅     |
| View ALL cases                           | ❌        | ✅          | ✅     |
| Change workflow state                    | ❌        | ✅          | ✅     |
| Schedule / update appointments           | ❌        | ✅          | ✅     |
| Mark appointment as missed               | ❌        | ✅          | ✅     |
| Edit High-Risk threshold (risk policy)   | ❌        | ✅          | ✅     |
| View program-wide KPI dashboard          | ❌        | ❌          | ✅     |
| Manage users / groups (Django admin)     | ❌        | ❌          | ✅     |

Permissions are enforced in two layers:

1. `accounts.permissions.role_required` — a decorator that returns
   `403 Forbidden` when a logged-in user with the wrong role accesses
   a view. Unauthenticated users are redirected to the login page.
2. Django `Groups` (`Operators`, `Supervisors`, `Program Admins`) kept
   in sync with `User.role` via `User.sync_groups()` — this keeps the
   built-in admin permissions and DRF permission classes working.

Every denied action is recorded on the case timeline with
`CaseEvent.Action.DENIED` so audits can see both successes and
failures.
