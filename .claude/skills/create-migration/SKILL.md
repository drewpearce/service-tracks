---
name: create-migration
description: Generate and review a new Alembic migration for ServiceTracks after a model change. Use when the user asks to create a database migration, add a column/table/index, or after editing files under backend/app/models/.
disable-model-invocation: true
---

# Create Migration

Generate an Alembic migration from current model changes and review it for safety before it gets applied. ServiceTracks uses async SQLAlchemy 2.0 with autogenerate.

## Steps

### 1. Confirm models are saved and the DB is current
The autogenerate diff is computed against the live dev DB at `head`. Bring it up to date first:

```bash
make migrate   # alembic upgrade head
```

If `make dev-db` Postgres isn't running, start it first: `make dev-db`.

### 2. Generate the migration
Always run alembic from `backend/` via uv. Use a short, descriptive slug:

```bash
cd backend && uv run alembic revision --autogenerate -m "<short description>"
```

This writes a new file under `backend/alembic/versions/`.

### 3. Review the generated file — REQUIRED
Open the new file and check it before trusting it. Autogenerate is not reliable for everything:

- **Reversibility:** `downgrade()` must actually undo `upgrade()`. Fill it in if empty.
- **Destructive ops:** flag any `op.drop_column` / `op.drop_table` / `op.drop_constraint`. Confirm the intent with the user — these lose data in prod.
- **Type changes:** column type alterations may need an explicit `postgresql_using` clause; autogenerate often omits it.
- **Data migrations:** autogenerate only diffs schema. If the change needs backfilling existing rows, add the data migration by hand.
- **Conventions:** `Uuid` PKs, `DateTime(timezone=True)`, server defaults where appropriate (match `001_initial_schema.py`).
- **Indexes/constraints:** new FKs and unique constraints picked up correctly?
- **No-op noise:** if autogenerate emitted spurious changes (e.g. it didn't detect the existing state), fix or discard.

### 4. Apply and verify
```bash
make migrate          # apply to dev DB
```
Then sanity-check it reverses cleanly:
```bash
cd backend && uv run alembic downgrade -1 && uv run alembic upgrade head
```

### 5. Report
Summarize: the migration filename, what it changes, whether `downgrade` is safe, and any destructive operations the user must consciously approve. Remind them migrations run automatically — confirm CI/deploy applies `alembic upgrade head` before pushing.
