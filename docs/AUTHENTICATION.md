# CyberTriage Authentication Demo

CyberTriage uses first-party password login with server-side sessions. It does
not use OAuth/OIDC or JWTs.

## First run

Open the web app. If the database has no accounts, CyberTriage displays the
initial setup form. Create the first account with a valid email, display name,
and a password of at least 12 characters. This first account receives the
`Admin` role and takes ownership of the existing unowned investigations, so
the demo data remains available.

After setup, an administrator creates accounts through `POST /api/auth/users`.
New accounts default to `Analyst`; an administrator can explicitly assign
`Admin`. There is no public registration endpoint.

## Authentication and session lifecycle

- Passwords are hashed with Python's standard-library
  `hashlib.pbkdf2_hmac("sha256", ...)`, 600,000 iterations, and a random
  16-byte salt. The encoded hash and salt are stored in `users.password_hash`;
  the plaintext password is not stored.
- Login issues a random opaque session ID in the `cybertriage_session` cookie.
  The cookie is `HttpOnly`, `SameSite=Lax`, path `/`, and expires after 8 hours.
  Set `CYBERTRIAGE_COOKIE_SECURE=1` when serving over HTTPS to enable `Secure`.
- The server stores only the SHA-256 digest of the session ID in
  `auth_sessions`. Sessions have an absolute 8-hour lifetime. There are no
  separate access or refresh tokens; users log in again when the session
  expires.
- Logout deletes the current session row and clears the cookie.
- The login response includes a CSRF token. The frontend holds it in memory and
  sends it as `X-CSRF-Token` on POST/PATCH/PUT/DELETE requests. It is not stored
  in localStorage.

## Roles and case access

- `Admin` can manage accounts and view all investigations.
- `Analyst` can work only with investigations they own.
- Authentication and CSRF checks run in the HTTP middleware in
  `backend/app/main.py`. Admin-only account operations check the role in their
  handlers. `_scope_clause` adds the owner condition to investigation and
  related evidence, finding, analysis, timeline, and dashboard queries.
- Attempting to read another analyst's record returns the same `404` as a
  missing record. This avoids confirming that another user's record exists.

## Viva API checks

With the backend running at `http://127.0.0.1:8000`:

```bash
# No cookie: protected API returns 401
curl -i http://127.0.0.1:8000/api/cases

# Check initial setup state
curl http://127.0.0.1:8000/api/auth/status
```

Create the initial administrator in the browser setup form. In browser DevTools,
show the `HttpOnly` session cookie and the `users.password_hash` value in
SQLite. For role/ownership demonstrations, create two analysts from an Admin
session using `POST /api/auth/users`, sign in separately, create a case as
Analyst A, and try to list or update that case as Analyst B. The case is absent
from B's list and the cross-owner update returns `404`. A request by an Analyst
to `GET /api/auth/users` returns `403`.
