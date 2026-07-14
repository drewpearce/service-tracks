# Spotify/YouTube Refresh-Token Reauth Handling — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When a Spotify/YouTube refresh token has expired (`400 invalid_grant`), mark the connection `needs_reauth`, stop retrying, and surface a clear reconnect prompt in the UI.

**Architecture:** Detect `invalid_grant` in the two token-refresh service functions; raise a new terminal `TokenReauthRequiredError` and set a distinct `needs_reauth` connection status. The sync engine already selects only `active` connections, so dead ones are auto-skipped; the sync loop additionally catches the terminal error if a token dies mid-sync. The frontend already receives per-connection `status`; three pages render a `needs_reauth` warning driven off it.

**Tech Stack:** FastAPI, async SQLAlchemy 2.0, httpx, structlog, pytest + respx; React + TypeScript SPA.

## Global Constraints

- Python deps via `uv` only. Type annotations required on all function signatures.
- Services use `db.flush()`, never `db.commit()` (routers own the transaction).
- Layering: routers → services → adapters (no skipping).
- structlog with keyword args (`logger.info("event", key=val)`), never f-strings.
- Backend tests are async (`asyncio_mode = "auto"`); external HTTP mocked with `respx`; per-test DB rollback (`backend/tests/conftest.py`). Test DB via `TEST_DATABASE_URL`.
- Frontend: all API calls via `apiClient()`; `types/api.ts` mirrors Pydantic manually; no frontend test suite (verify locally).
- New status value: `"needs_reauth"` — fits existing `StreamingConnection.status` `String(20)` column; **no migration**.
- Do **not** clear/null the stored refresh-token bytes (column is non-nullable; status gates use).
- Final gate: `make test` + `make lint` green.

---

### Task 1: Add `TokenReauthRequiredError` + detect `invalid_grant` in `refresh_spotify_token`

**Files:**
- Modify: `backend/app/services/streaming_service.py` (add exception near existing `SpotifyTokenError` ~line 24; edit `refresh_spotify_token` ~lines 37-76)
- Test: `backend/tests/test_token_reauth.py` (new)

**Interfaces:**
- Produces: `class TokenReauthRequiredError(Exception)` — raised when a refresh returns `invalid_grant` (terminal; caller must not retry). Consumed by Task 3.
- Produces: connection status string literal `"needs_reauth"`.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/test_token_reauth.py`. Follow existing refresh-token test setup in the repo (search `backend/tests/` for an existing test that builds a `StreamingConnection` and mocks `https://accounts.spotify.com/api/token` with `respx`; reuse its fixture/helpers for encryption and the church/connection rows).

```python
import httpx
import pytest
import respx

from app.services.streaming_service import (
    TokenReauthRequiredError,
    refresh_spotify_token,
)
from app.utils.encryption import decrypt


@respx.mock
async def test_spotify_refresh_invalid_grant_sets_needs_reauth(db_session, spotify_connection):
    # spotify_connection: an active StreamingConnection persisted for a church,
    # with a valid encrypted refresh token and platform="spotify".
    route = respx.post("https://accounts.spotify.com/api/token").mock(
        return_value=httpx.Response(400, json={"error": "invalid_grant"})
    )
    original_refresh = spotify_connection.refresh_token_encrypted

    with pytest.raises(TokenReauthRequiredError):
        await refresh_spotify_token(db_session, spotify_connection)

    assert route.call_count == 1  # no retry
    assert spotify_connection.status == "needs_reauth"
    # token bytes preserved (not cleared)
    assert spotify_connection.refresh_token_encrypted == original_refresh
    assert decrypt(spotify_connection.refresh_token_encrypted)  # still decryptable


@respx.mock
async def test_spotify_refresh_transient_error_sets_error(db_session, spotify_connection):
    respx.post("https://accounts.spotify.com/api/token").mock(
        return_value=httpx.Response(500, json={"error": "server_error"})
    )
    from app.services.streaming_service import SpotifyTokenError

    with pytest.raises(SpotifyTokenError):
        await refresh_spotify_token(db_session, spotify_connection)
    assert spotify_connection.status == "error"
```

> If no reusable `spotify_connection` fixture exists, create one in this test module (or `conftest.py`) that persists a `Church` + `StreamingConnection(platform="spotify", status="active", access_token_encrypted=encrypt("a"), refresh_token_encrypted=encrypt("r"), token_expires_at=<past>, external_user_id="u")`. Match how other tests build these rows.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_token_reauth.py -v`
Expected: FAIL — `ImportError: cannot import name 'TokenReauthRequiredError'`.

- [ ] **Step 3: Add the exception**

In `backend/app/services/streaming_service.py`, after the existing `YouTubeTokenError` class (~line 33):

```python
class TokenReauthRequiredError(Exception):
    """Raised when a refresh token is expired/revoked (invalid_grant).

    Terminal: the caller must NOT retry; the user has to reconnect. The
    connection's status is set to ``needs_reauth`` before this is raised.
    """

    pass
```

- [ ] **Step 4: Edit `refresh_spotify_token` to branch on `invalid_grant`**

Replace the current non-200 block in `refresh_spotify_token` (the `if response.status_code != 200:` branch, ~lines 59-64):

```python
    if response.status_code != 200:
        error_code: str | None = None
        try:
            error_code = response.json().get("error")
        except ValueError:
            pass
        if response.status_code == 400 and error_code == "invalid_grant":
            logger.warning(
                "spotify_refresh_token_expired",
                church_id=str(connection.church_id),
            )
            connection.status = "needs_reauth"
            await db.flush()
            raise TokenReauthRequiredError("Spotify refresh token expired; reconnection required")
        logger.error(
            "spotify_token_refresh_failed",
            status_code=response.status_code,
            error=error_code,
            church_id=str(connection.church_id),
        )
        connection.status = "error"
        await db.flush()
        raise SpotifyTokenError("Token refresh failed")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_token_reauth.py -v`
Expected: PASS (both tests).

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/streaming_service.py backend/tests/test_token_reauth.py
git commit -m "feat(sync): detect Spotify invalid_grant -> needs_reauth (#68)"
```

---

### Task 2: Detect `invalid_grant` in `refresh_youtube_token`

**Files:**
- Modify: `backend/app/services/streaming_service.py` (`refresh_youtube_token` ~lines 234-251 — the non-200 block; it already parses `error`/`error_description`)
- Test: `backend/tests/test_token_reauth.py` (extend)

**Interfaces:**
- Consumes: `TokenReauthRequiredError` and `"needs_reauth"` from Task 1.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_token_reauth.py`:

```python
@respx.mock
async def test_youtube_refresh_invalid_grant_sets_needs_reauth(db_session, youtube_connection):
    route = respx.post("https://oauth2.googleapis.com/token").mock(
        return_value=httpx.Response(400, json={"error": "invalid_grant"})
    )
    with pytest.raises(TokenReauthRequiredError):
        from app.services.streaming_service import refresh_youtube_token
        await refresh_youtube_token(db_session, youtube_connection)
    assert route.call_count == 1
    assert youtube_connection.status == "needs_reauth"


@respx.mock
async def test_youtube_refresh_transient_error_sets_error(db_session, youtube_connection):
    respx.post("https://oauth2.googleapis.com/token").mock(
        return_value=httpx.Response(503, json={"error": "unavailable"})
    )
    from app.services.streaming_service import YouTubeTokenError, refresh_youtube_token

    with pytest.raises(YouTubeTokenError):
        await refresh_youtube_token(db_session, youtube_connection)
    assert youtube_connection.status == "error"
```

> Add a `youtube_connection` fixture mirroring `spotify_connection` but `platform="youtube"`.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_token_reauth.py -k youtube -v`
Expected: FAIL — YouTube still raises `YouTubeTokenError` (not `TokenReauthRequiredError`) on invalid_grant.

- [ ] **Step 3: Add the invalid_grant branch to `refresh_youtube_token`**

In the existing `if response.status_code != 200:` block of `refresh_youtube_token` (it already computes `error_code`), insert the terminal branch **before** the existing `logger.error(...)`/`connection.status = "error"` lines:

```python
        if response.status_code == 400 and error_code == "invalid_grant":
            logger.warning(
                "youtube_refresh_token_expired",
                church_id=str(connection.church_id),
            )
            connection.status = "needs_reauth"
            await db.flush()
            raise TokenReauthRequiredError("YouTube refresh token expired; reconnection required")
```

(Leave the existing `logger.error("youtube_token_refresh_failed", ...)`, `connection.status = "error"`, `raise YouTubeTokenError(...)` as the fall-through for all other non-200s.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_token_reauth.py -v`
Expected: PASS (all four tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/streaming_service.py backend/tests/test_token_reauth.py
git commit -m "feat(sync): detect YouTube invalid_grant -> needs_reauth (#68)"
```

---

### Task 3: Handle a token dying mid-sync (skip-with-reason, don't throw)

**Files:**
- Modify: `backend/app/services/sync_service.py` (the per-connection sync loop's exception handling, ~lines 159-267)
- Test: `backend/tests/test_token_reauth.py` (extend) or the existing sync test module if one exists

**Interfaces:**
- Consumes: `TokenReauthRequiredError` from Task 1.

**Context:** `sync_plan` selects only `status == "active"` connections (`sync_service.py:57-59`), so `needs_reauth` connections are already excluded from future syncs — no change needed there. The only gap is a connection that is `active` at select time but whose token turns out to be expired when the adapter refreshes it mid-sync: `refresh_spotify_token`/`refresh_youtube_token` will set `needs_reauth` and raise `TokenReauthRequiredError`. The per-connection loop must catch it and record a clear reconnection outcome rather than a generic playlist error or an unhandled raise.

- [ ] **Step 1: Read the current per-connection exception handling**

Run: `sed -n '155,270p' backend/app/services/sync_service.py`
Identify the `try/except` wrapping each connection's playlist sync (the block that sets `playlist.sync_status = "error"` on exception, ~lines 250-267). Note the exact exception types already caught and the `SyncResult`/`platform_results` shape used.

- [ ] **Step 2: Write the failing test**

Add a test that drives `sync_plan` with one active Spotify connection whose token refresh returns `invalid_grant`, and asserts the sync completes without raising and records a `reconnection_required` (or equivalent) status for that platform rather than a generic `"error"`. Model it on any existing `sync_plan` test (search `backend/tests/` for `sync_plan`); reuse that test's PCO/plan/mapping fixtures and `respx` mocks, adding:

```python
respx.post("https://accounts.spotify.com/api/token").mock(
    return_value=httpx.Response(400, json={"error": "invalid_grant"})
)
```

Assert: `sync_plan(...)` returns normally (no exception); the Spotify platform result's status is the new reconnection status; `connection.status == "needs_reauth"`.

> If wiring a full `sync_plan` test is disproportionate, instead unit-test the new `except TokenReauthRequiredError` branch by asserting the branch sets the intended `sync_status`/reason on a `Playlist` given a patched adapter that raises `TokenReauthRequiredError`. Prefer the integration-style test if the repo already has `sync_plan` fixtures.

- [ ] **Step 3: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_token_reauth.py -k sync -v`
Expected: FAIL — currently `TokenReauthRequiredError` is either uncaught or collapses into generic `"error"`.

- [ ] **Step 4: Add a dedicated except branch**

In the per-connection loop, add an `except TokenReauthRequiredError` **before** the broad exception handler so it is not shadowed. Set the playlist/platform result to a clear reconnection status and continue to the next connection (do not re-raise). Use `"needs_reauth"` as the `sync_status` value (or, if `sync_status` is constrained to an existing vocabulary, use `"skipped"` and set a reason/`error_message` of `"reconnection_required"` — match the column's existing usage). Example shape (adapt to the actual result objects in this file):

```python
            except TokenReauthRequiredError:
                logger.warning(
                    "sync_connection_needs_reauth",
                    church_id=str(church_id),
                    platform=connection.platform,
                )
                # connection.status is already "needs_reauth" (set in the refresh fn)
                playlist.sync_status = "skipped"
                platform_results.append(
                    PlatformSyncResult(  # use the actual result type used in this file
                        platform=connection.platform,
                        sync_status="skipped",
                        error_message="reconnection_required",
                    )
                )
                continue
```

Import `TokenReauthRequiredError` at the top of `sync_service.py` from `app.services.streaming_service`.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_token_reauth.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/sync_service.py backend/tests/test_token_reauth.py
git commit -m "feat(sync): skip needs_reauth connection with reason instead of throwing (#68)"
```

---

### Task 4: Assert `needs_reauth` flows through `/api/streaming/status`

**Files:**
- Test: `backend/tests/test_token_reauth.py` (extend) — no production change expected.

**Context:** `streaming_status` already returns `status=conn.status` (`routers/streaming.py:455`), and `connected=(conn.status == "active")` stays unchanged by design (the UI drives the reconnect prompt off `status`, not `connected`). This task is a guard test confirming the passthrough.

- [ ] **Step 1: Write the test**

Add an authenticated request test (reuse the repo's authenticated `client` fixture + a church with a `needs_reauth` Spotify connection):

```python
async def test_streaming_status_exposes_needs_reauth(client, church_with_needs_reauth_spotify):
    resp = await client.get("/api/streaming/status")
    assert resp.status_code == 200
    conns = resp.json()["connections"]
    spotify = next(c for c in conns if c["platform"] == "spotify")
    assert spotify["status"] == "needs_reauth"
    assert spotify["connected"] is False  # connected semantics unchanged
```

- [ ] **Step 2: Run test**

Run: `cd backend && uv run pytest tests/test_token_reauth.py -k status -v`
Expected: PASS with no production change. If it FAILS, do not weaken the test — fix the passthrough in `routers/streaming.py`.

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_token_reauth.py
git commit -m "test(sync): assert needs_reauth surfaces via /api/streaming/status (#68)"
```

---

### Task 5: Surface `needs_reauth` on the Streaming setup cards

**Files:**
- Modify: `frontend/src/pages/SetupStreaming.tsx` (connection derivation ~lines 207-210; Spotify card ~lines 258-300; YouTube card ~lines 315-345)

**Context:** `spotifyConnection`/`youtubeConnection` are the raw `StreamingConnectionStatus` objects (have `.status`). Today `spotifyConnected = connection?.connected` gates the "Connected as X" badge, the Reconnect button label, and the reset/disconnect controls. A `needs_reauth` connection has `connected: false` but is present in the list with `status: "needs_reauth"`.

- [ ] **Step 1: Derive presence + reauth flags**

After the existing `spotifyConnection`/`youtubeConnection` lines (~207-210), add:

```tsx
  const spotifyPresent = spotifyConnection != null;
  const spotifyNeedsReauth = spotifyConnection?.status === "needs_reauth";
  const youtubePresent = youtubeConnection != null;
  const youtubeNeedsReauth = youtubeConnection?.status === "needs_reauth";
```

- [ ] **Step 2: Gate controls on presence, add the warning (Spotify card)**

In the Spotify card: change the reset/disconnect controls and the button's "Reconnect" label to gate on `spotifyPresent` instead of `spotifyConnected` (so they show for a dead-but-present connection). Keep the green "Connected as {id}" badge gated on `spotifyConnected` (healthy only). Add an amber warning block, rendered when `spotifyNeedsReauth`:

```tsx
              {spotifyNeedsReauth && (
                <div className="mt-3 rounded-xl border border-amber-200 bg-amber-50 p-3 text-[13px] text-amber-800">
                  Reconnection required — your Spotify sign-in expired. Reconnect to resume syncing.
                </div>
              )}
```

Button label becomes: `connectingSpotify ? "Redirecting…" : spotifyPresent ? "Reconnect" : "Connect Spotify"`. Button style: use the "outline/reconnect" style when `spotifyPresent`, primary when absent.

- [ ] **Step 3: Mirror for the YouTube card**

Apply the identical treatment to the YouTube card using `youtubePresent` / `youtubeNeedsReauth`, with copy "your YouTube Music sign-in expired."

- [ ] **Step 4: Verify locally (typecheck + visual)**

Run: `cd frontend && npx tsc --noEmit` → expect no errors.
Then run the app (`make backend` on a free port + `make frontend`), and with a church whose Spotify connection row is manually set to `status='needs_reauth'` in the dev DB, confirm the amber warning + "Reconnect" button render on `/setup/streaming`. (See Task 8 for a scripted way to set the status.)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/SetupStreaming.tsx
git commit -m "feat(ui): show reconnect-required warning on streaming setup cards (#68)"
```

---

### Task 6: Surface `needs_reauth` on the Settings page

**Files:**
- Modify: `frontend/src/pages/Settings.tsx` (status load ~lines 50-56; connection display / empty-state ~line 163)

**Context:** Settings loads `status.connections` and filters `c.connected` into `connectedPlatforms` (active only). A `needs_reauth` connection is in `status.connections` with `connected: false`, so it's currently dropped silently.

- [ ] **Step 1: Compute needs-reauth platforms from the loaded status**

Where `status.connections` is available (~line 50), also derive the platforms needing reauth and store in state:

```tsx
        const needsReauth = status.connections
          .filter((c) => c.status === "needs_reauth")
          .map((c) => c.platform);
        setReauthPlatforms(needsReauth);
```

Add `const [reauthPlatforms, setReauthPlatforms] = useState<string[]>([]);`.

- [ ] **Step 2: Render a reconnect prompt**

Near the connections section, when `reauthPlatforms.length > 0`, render an amber notice per platform with a link to `/setup/streaming`:

```tsx
        {reauthPlatforms.map((p) => (
          <div key={p} className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-[13px] text-amber-800">
            {PLATFORM_LABEL[p] ?? p} needs to be reconnected — sign-in expired.{" "}
            <Link to="/setup/streaming" className="underline font-medium">Reconnect</Link>
          </div>
        ))}
```

Reuse the existing `PLATFORM_LABEL` map if present in this file; otherwise inline the label. Ensure `Link` is imported from `react-router-dom`.

- [ ] **Step 3: Verify locally**

Run: `cd frontend && npx tsc --noEmit` → no errors. Visually confirm the Settings notice with a `needs_reauth` connection in the dev DB.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Settings.tsx
git commit -m "feat(ui): show reconnect prompt on Settings for expired connections (#68)"
```

---

### Task 7: Dashboard banner when any connection needs reauth

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx` (uses `data.streaming_connections`, which includes `status`)

- [ ] **Step 1: Derive the flag**

Near the existing `spotifyConnected` derivation (~line 94):

```tsx
  const reauthPlatforms = data.streaming_connections
    .filter((c) => c.status === "needs_reauth")
    .map((c) => c.platform);
```

- [ ] **Step 2: Render the banner**

At the top of the dashboard body (before the main content, after the hero), render when `reauthPlatforms.length > 0`:

```tsx
        {reauthPlatforms.length > 0 && (
          <div className="mx-10 mt-6 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-[13px] text-amber-800">
            Syncing is paused for {reauthPlatforms.map((p) => PLATFORM_LABEL[p] ?? p).join(" and ")} —
            the sign-in expired.{" "}
            <Link to="/setup/streaming" className="underline font-medium">Reconnect now</Link>
          </div>
        )}
```

Use the page's existing label map / `Link` import (add if missing). Match the page's container padding conventions.

- [ ] **Step 3: Verify locally**

Run: `cd frontend && npx tsc --noEmit` → no errors. Confirm the banner appears on `/dashboard` with a `needs_reauth` connection in the dev DB and links to setup.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx
git commit -m "feat(ui): dashboard banner when a streaming connection needs reauth (#68)"
```

---

### Task 8: Full quality gate + manual end-to-end verification

**Files:** none (verification only).

- [ ] **Step 1: Backend gate**

Run: `cd backend && uv run pytest -q && uv run ruff check && uv run ruff format --check`
Expected: all pass; new `needs_reauth` tests included in the count.

- [ ] **Step 2: Frontend gate**

Run: `cd frontend && npx tsc --noEmit && npm run lint`
Expected: no errors.

- [ ] **Step 3: Manual end-to-end**

Boot the app (`make backend` on a free port + `make frontend`). Set a connection to `needs_reauth` in the dev DB, e.g.:

```bash
docker exec -it st-design-db-1 psql -U worship_flow -d service_tracks \
  -c "UPDATE streaming_connection SET status='needs_reauth' WHERE platform='spotify';"
```

Confirm: (a) Dashboard shows the amber banner; (b) `/setup/streaming` shows the amber warning + "Reconnect"; (c) `/settings` shows the reconnect notice; (d) clicking Reconnect starts the OAuth flow. Revert the row (`status='active'`) and confirm all warnings disappear.

- [ ] **Step 4: Final commit (if any verification fixes were needed)**

```bash
git add -A && git commit -m "chore(sync): verification fixes for reauth handling (#68)"
```

---

## Self-Review

**Spec coverage:**
- Detect `invalid_grant`, `needs_reauth`, no retry, keep token → Tasks 1 (Spotify), 2 (YouTube). ✅
- New `TokenReauthRequiredError` distinct from transient errors → Task 1. ✅
- sync_service skip-with-reason, don't throw → Task 3 (plus the existing `active`-only select auto-skips dead connections). ✅
- UI surfacing on cards + Settings + Dashboard → Tasks 5, 6, 7. ✅
- Tests: invalid_grant vs transient, both platforms, status passthrough, sync skip → Tasks 1–4. ✅
- Out of scope (notifications #16, scheduler re-enable, nulling token bytes) → not in any task. ✅

**Placeholder scan:** No TBD/"handle errors"/"similar to". The two spots that depend on repo-specific shapes (the `PlatformSyncResult` type name in Task 3; the `PLATFORM_LABEL` map in Tasks 6–7) are called out explicitly with "use the actual type/map in this file" instructions, because the exact names must be read from the code at implementation time.

**Type consistency:** `TokenReauthRequiredError`, `"needs_reauth"`, log events `spotify_refresh_token_expired`/`youtube_refresh_token_expired`, and `error_code == "invalid_grant"` are used consistently across tasks. `connected` semantics deliberately unchanged; UI keys off `status`.
