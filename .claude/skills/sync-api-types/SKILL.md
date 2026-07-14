---
name: sync-api-types
description: Keep frontend/src/types/api.ts in sync with backend Pydantic schemas. Use when a backend schema in backend/app/schemas/ is added or changed, when a route's request/response shape changes, or when the user mentions API types being out of sync.
---

# Sync API Types

ServiceTracks mirrors backend Pydantic v2 schemas into `frontend/src/types/api.ts` **by hand** — there is no codegen. This skill finds drift between the two and proposes the matching TypeScript edits. This is a documented gotcha in CLAUDE.md.

## Steps

### 1. Identify what changed on the backend
If invoked after a schema edit, diff it:

```bash
git diff main...HEAD -- backend/app/schemas/
```

Otherwise, ask which schema/route changed, or scan `backend/app/schemas/` for the relevant response/request models.

### 2. Map Pydantic → TypeScript
For each changed schema, locate the corresponding interface in `frontend/src/types/api.ts` and reconcile it. Conversion rules:

| Pydantic | TypeScript |
|----------|-----------|
| `str` | `string` |
| `int` / `float` | `number` |
| `bool` | `boolean` |
| `uuid.UUID` | `string` |
| `datetime` / `date` | `string` (ISO) |
| `Optional[T]` / `T \| None` | `T \| null` (and mark the field optional `?` only if it can be absent, not just null) |
| `list[T]` | `T[]` |
| `dict[str, T]` | `Record<string, T>` |
| `Enum` | union of string literals |
| nested `BaseModel` | the corresponding interface |

Field names: Pydantic models here use snake_case and (unless an alias is set) serialize as snake_case — keep the TS fields snake_case to match the wire format. If a schema sets `alias`/`serialization_alias`, use the alias.

### 3. Distinguish request vs response
CLAUDE.md mandates separate request and response schemas. Make sure you update the right TS interface — a response schema maps to the type the frontend *reads*; a request schema maps to what `apiClient()` *sends*.

### 4. Propose edits, then apply on approval
Show the diff to `frontend/src/types/api.ts` and a one-line rationale per change. After approval, apply with Edit. Then type-check:

```bash
cd frontend && npx tsc --noEmit
```

Fix any call sites the type change broke, or list them for the user if the change is intentional and wide-reaching.

### 5. Report
List which interfaces changed and whether `tsc` passes. Flag any backend field you couldn't confidently map (e.g. a custom validator or computed serializer) so the user can confirm the wire shape.
