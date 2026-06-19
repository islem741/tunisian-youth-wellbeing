# Threat Model (Track B — Security & Privacy)

## Assets

1. Synthetic student records (simulating sensitive engagement data).
2. SERS entries (component scores + free-text notes).
3. SERSPolicy configuration (impacts which students are flagged HIGH).
4. User accounts (password hashes, role assignments).
5. Audit log (CaseEvent — immutable chain of custody).

## Abuse cases

| # | Actor                | Abuse case                                     | Mitigation |
|---|----------------------|------------------------------------------------|------------|
| 1 | Curious Operator     | Reads another school's student cases           | `_scoped_entries` in `cases/views.py` restricts Operators to their own submissions + their school. Cross-school access returns 403 and is logged as `CaseEvent(action=SECURITY)`. |
| 2 | Operator             | Transitions a case or edits SERS policy        | `@role_required(Role.SUPERVISOR/ADMIN)` on transition + policy views. Blocked with HTTP 403. |
| 3 | Attacker             | CSRF-forged POST to change SERS weights        | `CsrfViewMiddleware` on every form; no AJAX for destructive actions. |
| 4 | Attacker             | Submits out-of-range component values          | `SERSEntry.clean()` raises `ValidationError` with a user-facing message; no DB write. Tested in `test_sers_scoring.py`. |
| 5 | Attacker             | SQL injection via search or URL parameters     | Django ORM parameterises all queries; no raw SQL used. |
| 6 | Insider              | Exfiltrates bulk CSV of all cases              | `export_cases_csv` uses `_scoped_entries` — only the caller's accessible cases. Only Supervisor/Admin can reach this view. |
| 7 | Attacker             | Brute-force login                              | Django's `LoginView` + PBKDF2 password hashing. Production hardening: add `django-axes`. |
| 8 | Attacker             | Injects malicious CSV rows                     | `ingest_sers_csv` validates each row; malformed rows are rejected with per-row error messages. Full batch rolled back atomically. |

## Data classification

| Field                     | Classification                                |
|---------------------------|-----------------------------------------------|
| `first_name`, `last_name` | Pseudo-PII (synthetic here; PII in production)|
| `notes`                   | Free text — high sensitivity, role-gated      |
| SERS component scores     | Sensitive engagement indicators, role-gated   |
| `risk_explanation`        | Derived — visible only in case detail view    |

## Sensitive-field handling

- `notes` are never exposed in the case list or CSV export.
- The CSV export omits free-text `notes` (add opt-in only).
- Django admin is restricted to `admin1` (`is_staff=True`, `is_superuser=True`).
- Every denied cross-school access is written to `CaseEvent(action=SECURITY)`.

## Future hardening (out of scope for this exam)

- Add `django-axes` rate limiter for login attempts.
- Rotate `SECRET_KEY` from a secrets manager (e.g. AWS Secrets Manager).
- Enable `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, HSTS in production.
- Per-field encryption for `notes` using `django-cryptography`.
