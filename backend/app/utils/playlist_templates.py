"""Utility for rendering playlist name/description templates."""

from datetime import date


class _SafeDict(dict):
    """dict subclass that returns the key placeholder for missing keys."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def render_template(
    template: str,
    *,
    plan_date: date | None,
    plan_title: str | None,
    church_name: str,
) -> str:
    """Render a playlist name/description template.

    Supported variables:
    - {date}        — "April 7, 2026" (no leading zero on day)
    - {date_iso}    — "2026-04-07"
    - {title}       — plan title
    - {church_name} — church name

    Unknown variables are passed through unchanged (no KeyError).
    """
    if plan_date is not None:
        # Use %-d on POSIX for no leading zero; on Windows use %#d
        try:
            formatted_date = plan_date.strftime("%-d")
        except ValueError:
            formatted_date = plan_date.strftime("%#d")
        date_str = plan_date.strftime(f"%B {formatted_date}, %Y")
        date_iso = plan_date.isoformat()
    else:
        date_str = ""
        date_iso = ""

    context = _SafeDict(
        date=date_str,
        date_iso=date_iso,
        title=plan_title or "",
        church_name=church_name,
    )
    return template.format_map(context)
