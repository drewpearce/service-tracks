"""Unit tests for app.utils.playlist_templates.render_template."""

from datetime import date

from app.utils.playlist_templates import render_template


def test_render_date_variable():
    """date variable formats to 'Month D, YYYY' with no leading zero."""
    result = render_template(
        "Worship for {date}",
        plan_date=date(2026, 4, 7),
        plan_title="Sunday Service",
        church_name="Grace Church",
    )
    assert result == "Worship for April 7, 2026"


def test_render_date_no_leading_zero():
    """Single-digit day must not have a leading zero."""
    result = render_template(
        "{date}",
        plan_date=date(2026, 3, 1),
        plan_title=None,
        church_name="Church",
    )
    assert result == "March 1, 2026"


def test_render_date_two_digit_day():
    """Two-digit day is rendered correctly."""
    result = render_template(
        "{date}",
        plan_date=date(2026, 12, 25),
        plan_title=None,
        church_name="Church",
    )
    assert result == "December 25, 2026"


def test_render_date_iso_variable():
    """date_iso variable formats to ISO 8601."""
    result = render_template(
        "Set for {date_iso}",
        plan_date=date(2026, 4, 7),
        plan_title=None,
        church_name="Church",
    )
    assert result == "Set for 2026-04-07"


def test_render_title_variable():
    """{title} is replaced with plan_title."""
    result = render_template(
        "{title} playlist",
        plan_date=date(2026, 4, 7),
        plan_title="Easter Sunday",
        church_name="Church",
    )
    assert result == "Easter Sunday playlist"


def test_render_church_name_variable():
    """{church_name} is replaced with the church name."""
    result = render_template(
        "{church_name} Worship",
        plan_date=date(2026, 4, 7),
        plan_title=None,
        church_name="Hillside Community Church",
    )
    assert result == "Hillside Community Church Worship"


def test_render_multiple_variables():
    """Multiple variables are all substituted in a single template."""
    result = render_template(
        "{church_name} — {date}",
        plan_date=date(2026, 4, 12),
        plan_title="Palm Sunday",
        church_name="Grace",
    )
    assert result == "Grace — April 12, 2026"


def test_render_unknown_variable_passthrough():
    """Unknown variables are passed through unchanged (no KeyError)."""
    result = render_template(
        "Hello {unknown_var}",
        plan_date=date(2026, 4, 7),
        plan_title=None,
        church_name="Church",
    )
    assert result == "Hello {unknown_var}"


def test_render_none_date():
    """When plan_date is None, date variables produce empty strings."""
    result = render_template(
        "Service on {date} ({date_iso})",
        plan_date=None,
        plan_title=None,
        church_name="Church",
    )
    assert result == "Service on  ()"


def test_render_none_title():
    """When plan_title is None, {title} produces an empty string."""
    result = render_template(
        "{title} Worship",
        plan_date=date(2026, 4, 7),
        plan_title=None,
        church_name="Church",
    )
    assert result == " Worship"


def test_render_default_name_template():
    """Default name template produces expected output."""
    result = render_template(
        "{church_name} Worship",
        plan_date=date(2026, 4, 7),
        plan_title="Sunday Service",
        church_name="First Baptist",
    )
    assert result == "First Baptist Worship"


def test_render_default_description_template():
    """Default description template produces expected output."""
    result = render_template(
        "Worship set for {date}",
        plan_date=date(2026, 4, 7),
        plan_title=None,
        church_name="Church",
    )
    assert result == "Worship set for April 7, 2026"
