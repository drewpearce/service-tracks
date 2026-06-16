"""Well-known URIs (RFC 8615), including security.txt (RFC 9116).

Served outside the /api prefix so the AuthMiddleware passes them through
unauthenticated. Registered as a router (before the SPA catch-all in main.py)
so it takes precedence over the index.html fallback.
"""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter(tags=["well-known"])

# RFC 9116 security.txt. The Expires field is mandatory and should be < 1 year out;
# bump it on each review. Ensure security@service-tracks.com is a deliverable mailbox.
_SECURITY_TXT = """\
Contact: mailto:security@service-tracks.com
Expires: 2027-06-16T00:00:00.000Z
Preferred-Languages: en
Canonical: https://service-tracks.com/.well-known/security.txt
"""


@router.get("/.well-known/security.txt", response_class=PlainTextResponse, include_in_schema=False)
@router.get("/security.txt", response_class=PlainTextResponse, include_in_schema=False)
async def security_txt() -> str:
    return _SECURITY_TXT
