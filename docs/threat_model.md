# Threat model (Track B — Security & Privacy)

## Assets

1. Synthetic student records (simulating sensitive psychosocial data).
2. Stress assessments (component scores + free-text notes).
3. Risk-policy configuration (impacts how many cases are flagged).
4. User accounts (password hashes, role assignment).

## Abuse cases

| # | Actor                  | Abuse case                             | Mitigation |
|---|------------------------|-----------------------------------------|------------|
| 1 | Curious Operator       | Reads another school's students         | View-level scoping (`_scoped_assessments`) restricts Operators to their school. |
| 2 | Disgruntled Operator   | Escalates/closes cases to hide issues   | Only Supervisor/Admin can call `case_transition`; denied attempts return 403 and are logged as `DENIED` events. |
| 3 | Attacker               | Submits CSRF forged POST to change policy | Django `CsrfViewMiddleware` on every form; AJAX not used for destructive actions. |
| 4 | Attacker               | Tries impossible/overflow scores        | `StressAssessment.clean()` raises `ValidationError`; the form rejects the submission with a friendly message; no DB write. |
| 5 | Attacker               | Tries SQL injection via search / URL    | Django ORM parametrizes all queries; no raw SQL. |
| 6 | Insider                | Exfiltrates large CSV of cases          | `export_cases_csv` only exports cases the user can already see (`_scoped_assessments`). |
| 7 | Attacker               | Brute-forces login                      | Django's `LoginView` + password hashers; in production, add `django-axes` or rate-limit. |

## Data classification

| Field                     | Classification                       |
|---------------------------|---------------------------------------|
| `first_name`, `last_name` | Pseudo-PII (synthetic here). Would be PII in prod. |
| `notes`                   | Free text — high sensitivity.        |
| Component scores          | Sensitive indicator, role-gated.     |

## Sensitive-field handling

- Notes are never exposed outside the case detail view.
- The CSV export omits free-text notes on purpose (add-opt-in only).
- Django admin is restricted to `admin1` (superuser + `is_staff`).

## Future hardening (out of scope for this exam)

- Add `django-axes` rate limiter.
- Rotate `SECRET_KEY` from a secret manager.
- Turn on `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, HSTS in
  production settings.
- Add per-field encryption for `notes` using `django-cryptography`.
