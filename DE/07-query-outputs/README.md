# Query outputs

`sqlite-query-output.txt` contains actual output from running all 12 statements
in `../06-queries.sql` against an isolated copy of the repository's SQLite
database. The script's inserts, update, and delete are enclosed in a
transaction and rolled back. The source `backend/cybertriage.db` was not used
as the writable query target.

The execution environment was SQLite through Python's standard `sqlite3`
module. Local PostgreSQL was checked with `pg_isready` and did not respond; no
`DATABASE_URL` was configured. Therefore, no PostgreSQL execution or screenshot
is claimed.

When PostgreSQL is available, run from the repository root:

```bash
psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -a -f DE/06-queries.sql \
  | tee DE/07-query-outputs/postgresql-query-output.txt
```

The query file rolls its demonstration changes back. For a screenshot, capture
the terminal showing the command, the result rows for SELECT/RETURNING
statements, and the final `ROLLBACK` line. Record the PostgreSQL version and
database name in a short header; do not include credentials in the screenshot.
