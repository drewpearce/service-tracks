from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

limiter = Limiter(key_func=get_remote_address)


def church_id_key(request: Request) -> str:
    """Rate limit key function keyed on church_id for tenant-scoped limits.

    Falls back to IP address if church_id is not set (shouldn't happen
    for authenticated endpoints, but provides a safe fallback).
    """
    church_id = getattr(request.state, "church_id", None)
    if church_id is None:
        return get_remote_address(request)
    return str(church_id)
