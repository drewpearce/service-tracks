# Handle Spotify/YouTube refresh-token expiration (needs_reauth)

**Issue:** #68 · **Date:** 2026-07-14 · **Priority:** high (Spotify enforcement for existing apps begins 2026-07-20)

## Problem

Spotify now expires Authorization-Code refresh tokens 6 months after authorization
([announcement](https://developer.spotify.com/blog/2026-06-18-refresh-token-expiration)).
On expiry the token endpoint returns `400 {"error": "invalid_grant"}`. Spotify's required
handling: do **not** retry — discard the token and send the user through reauthorization.
Google's token endpoint returns the same `400 invalid_grant` for an expired/revoked refresh
token, so YouTube has the identical failure shape.

Today, `refresh_spotify_token` / `refresh_youtube_token`
(`backend/app/services/streaming_service.py`) treat **any** non-200 refresh response the same:
log, set `connection.status = "error"`, raise `SpotifyTokenError` / `YouTubeAuthError`. This
fails safe (no crash/retry-loop) but has three gaps:

- **A** — a terminal `invalid_grant` is indistinguishable from a transient 500/timeout.
- **B** — the dead state is invisible: the frontend reads only `connection.connected`, never
  `status`, so a church with a dead token still sees "Connected" and is never prompted to
  reconnect. Syncs silently stop.
- **C** — no proactive notification (out of scope here — issue #16).

## Approach

Distinguish the failure type by parsing the refresh error body, and introduce a distinct
`needs_reauth` connection status that the UI surfaces as a reconnect prompt.

### Backend

1. **New status value:** `"needs_reauth"` alongside existing `"active"` / `"error"`. Fits the
   existing `StreamingConnection.status` `String(20)` column — **no migration**.
2. **New exception:** `TokenReauthRequiredError` (streaming service/adapters layer) meaning
   "terminal — user must reconnect." Distinct from the existing transient `*TokenError`.
3. **`refresh_spotify_token` / `refresh_youtube_token`:** on a non-200 response, parse the JSON
   body:
   - body error == `invalid_grant` → set `status = "needs_reauth"`, flush, raise
     `TokenReauthRequiredError`. Do **not** retry. Token bytes are left in place (column is
     non-nullable; the status gates all use, and a reconnect overwrites them). Log a distinct
     event (e.g. `spotify_refresh_token_expired`).
   - any other non-200 → unchanged: `status = "error"` (transient), token preserved, existing
     exception raised.
4. **Sync path:** `sync_service` treats a `needs_reauth` connection as **skip-with-reason** —
   record a clear "reconnection required" outcome in the sync log/result rather than throwing an
   opaque error. (Scheduler church-selection is currently stubbed at `scheduler.py:112`, so no
   scheduler change is needed now.)

### Frontend

`/api/streaming/status` already returns per-connection `status` (`schemas/streaming.py`); the
frontend currently ignores it.

5. **Connection cards** (`SetupStreaming.tsx`, and the connection display in `Settings.tsx`):
   when `status === "needs_reauth"`, show an amber warning ("Reconnection required — sign-in
   expired. Reconnect to resume syncing.") with the existing Reconnect button as the CTA.
   `status === "error"` shows a softer "temporary problem, syncing will retry" note.
6. **Dashboard:** amber banner when any connection is `needs_reauth`, linking to the streaming
   setup page.

## Testing

- Spotify `invalid_grant` 400 → `status == "needs_reauth"`, `TokenReauthRequiredError` raised, no
  retry; YouTube `invalid_grant` 400 → same.
- Transient 500 on refresh → `status == "error"`, token preserved, existing exception (regression
  guard).
- `/api/streaming/status` reflects `needs_reauth` through to the response body.
- A sync against a `needs_reauth` connection is skipped with a clear reason, not an exception.
- (Frontend has no test suite per project conventions — covered by manual/local verification.)

## Out of scope

- Proactive email/push notification on disconnect (issue #16).
- Scheduler church-selection re-enablement (`scheduler.py:112`) — separate follow-up.
- Physically clearing/nulling the stored refresh-token bytes (would require a migration; status
  gating is sufficient).

## Acceptance criteria (from #68)

- [ ] `invalid_grant` on refresh is distinguished from transient failures and does not retry
- [ ] Dead connection is clearly surfaced in the UI with a reconnect prompt
- [ ] YouTube refresh path handled equivalently
- [ ] Tests cover invalid_grant vs transient failure
