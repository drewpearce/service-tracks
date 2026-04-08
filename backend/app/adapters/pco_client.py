"""PCO (Planning Center Online) API adapter.

Encapsulates all HTTP calls to the PCO API behind a clean interface.
Credentials are passed as plaintext strings (already decrypted by the caller).
"""

import httpx
import structlog

from app.schemas.pco import Plan, PlanSong, ServiceType

logger = structlog.get_logger(__name__)

PCO_BASE_URL = "https://api.planningcenteronline.com"
REQUEST_TIMEOUT = 15.0


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class PcoApiError(Exception):
    """Base exception for PCO API errors."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class PcoAuthError(PcoApiError):
    """Raised on 401 responses (invalid credentials)."""


class PcoRateLimitError(PcoApiError):
    """Raised on 429 responses."""

    def __init__(self, message: str, retry_after: int = 60, status_code: int | None = 429):
        super().__init__(message, status_code=status_code)
        self.retry_after = retry_after


class PcoServerError(PcoApiError):
    """Raised on 5xx responses."""


# ---------------------------------------------------------------------------
# PcoClient
# ---------------------------------------------------------------------------


class PcoClient:
    """Stateless PCO API client. Instantiate per-request with decrypted credentials."""

    def __init__(self, app_id: str, secret: str) -> None:
        self.app_id = app_id
        self.secret = secret

    async def _request(self, method: str, path: str, params: dict | None = None) -> httpx.Response:
        """Make an authenticated request to the PCO API."""
        auth = httpx.BasicAuth(self.app_id, self.secret)
        async with httpx.AsyncClient(
            base_url=PCO_BASE_URL,
            auth=auth,
            timeout=REQUEST_TIMEOUT,
        ) as http_client:
            try:
                response = await http_client.request(method, path, params=params)
            except httpx.HTTPError as exc:
                raise PcoApiError(f"PCO API network error: {exc}") from exc

        # Rate limit header inspection
        rate_limit_str = response.headers.get("X-PCO-API-Request-Rate-Limit")
        rate_count_str = response.headers.get("X-PCO-API-Request-Rate-Count")
        if rate_limit_str and rate_count_str:
            try:
                rate_limit = int(rate_limit_str)
                rate_count = int(rate_count_str)
                if rate_count > rate_limit * 0.8:
                    logger.warning(
                        "PCO rate limit approaching",
                        rate_count=rate_count,
                        rate_limit=rate_limit,
                    )
            except ValueError:
                pass  # malformed headers; ignore

        # Error handling
        if response.status_code == 401:
            raise PcoAuthError("PCO authentication failed: invalid credentials", status_code=401)
        if response.status_code == 429:
            retry_after_str = response.headers.get("Retry-After", "60")
            try:
                retry_after = int(retry_after_str)
            except ValueError:
                retry_after = 60
            raise PcoRateLimitError(
                "PCO rate limit exceeded",
                retry_after=retry_after,
                status_code=429,
            )
        if 500 <= response.status_code <= 599:
            raise PcoServerError(
                f"PCO server error: {response.status_code}",
                status_code=response.status_code,
            )
        if response.status_code >= 400:
            raise PcoApiError(
                f"PCO API error: {response.status_code}",
                status_code=response.status_code,
            )

        return response

    async def validate_credentials(self) -> bool:
        """Validate the stored credentials against the PCO API.

        Returns True if credentials are valid, False if invalid (401).
        Re-raises other PCO errors.
        """
        try:
            await self._request("GET", "/services/v2/service_types")
            return True
        except PcoAuthError:
            return False

    async def get_service_types(self) -> list[ServiceType]:
        """Fetch all service types for the connected PCO account."""
        response = await self._request("GET", "/services/v2/service_types")
        data = response.json()["data"]
        return [ServiceType(id=item["id"], name=item["attributes"]["name"]) for item in data]

    async def get_service_type(self, service_type_id: str) -> ServiceType | None:
        """Fetch a single service type by ID. Returns None if not found (404)."""
        try:
            response = await self._request("GET", f"/services/v2/service_types/{service_type_id}")
        except PcoApiError as exc:
            if exc.status_code == 404:
                return None
            raise
        data = response.json()["data"]
        return ServiceType(id=data["id"], name=data["attributes"]["name"])

    async def get_upcoming_plans(self, service_type_id: str) -> list[Plan]:
        """Fetch upcoming plans for a service type (up to 4, sorted by date)."""
        response = await self._request(
            "GET",
            f"/services/v2/service_types/{service_type_id}/plans",
            params={"filter": "future", "per_page": "4", "order": "sort_date"},
        )
        data = response.json()["data"]
        plans = []
        for item in data:
            attrs = item["attributes"]
            plans.append(
                Plan(
                    id=item["id"],
                    title=attrs.get("title") or "",
                    sort_date=attrs.get("sort_date", ""),
                    series_title=attrs.get("series_title"),
                )
            )
        # Safety sort — PCO already returns sorted, but be defensive
        plans.sort(key=lambda p: p.sort_date)
        return plans

    async def get_plan(self, service_type_id: str, plan_id: str) -> Plan | None:
        """Fetch metadata (title, date) for a single plan."""
        response = await self._request(
            "GET",
            f"/services/v2/service_types/{service_type_id}/plans/{plan_id}",
        )
        data = response.json().get("data")
        if not data:
            return None
        attrs = data["attributes"]
        return Plan(
            id=data["id"],
            title=attrs.get("title") or "",
            sort_date=attrs.get("sort_date", ""),
            series_title=attrs.get("series_title"),
        )

    async def get_plan_songs(self, service_type_id: str, plan_id: str) -> list[PlanSong]:
        """Fetch songs for a specific plan, preserving plan order.

        Non-song items (headers, media) are filtered out.
        """
        response = await self._request(
            "GET",
            f"/services/v2/service_types/{service_type_id}/plans/{plan_id}/items",
            params={"include": "song", "per_page": "50"},
        )
        body = response.json()

        # Build a lookup of included Song resources
        included = body.get("included", [])
        song_lookup: dict[str, dict] = {item["id"]: item for item in included if item["type"] == "Song"}

        songs: list[PlanSong] = []
        for item in body["data"]:
            song_rel = item.get("relationships", {}).get("song", {}).get("data")
            if not song_rel:
                # Non-song item (header, media, etc.) — skip
                continue
            song_id = song_rel["id"]
            song = song_lookup.get(song_id)
            if song is None:
                continue
            title = song["attributes"].get("title", "")
            artist = song["attributes"].get("author") or None
            songs.append(PlanSong(pco_song_id=song_id, title=title, artist=artist))

        return songs
