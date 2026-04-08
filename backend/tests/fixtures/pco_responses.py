"""Realistic mock PCO JSON:API response data for use in tests."""

VALID_SERVICE_TYPES_RESPONSE = {
    "data": [
        {
            "type": "ServiceType",
            "id": "111",
            "attributes": {"name": "Sunday Morning"},
        },
        {
            "type": "ServiceType",
            "id": "222",
            "attributes": {"name": "Wednesday Night"},
        },
    ]
}

SINGLE_SERVICE_TYPE_RESPONSE = {
    "data": {
        "type": "ServiceType",
        "id": "111",
        "attributes": {"name": "Sunday Morning"},
    }
}

UPCOMING_PLANS_RESPONSE = {
    "data": [
        {
            "type": "Plan",
            "id": "1001",
            "attributes": {
                "title": "Easter Sunday",
                "sort_date": "2026-04-05",
                "series_title": "Easter Series",
            },
        },
        {
            "type": "Plan",
            "id": "1002",
            "attributes": {
                "title": "Regular Service",
                "sort_date": "2026-04-12",
                "series_title": None,
            },
        },
    ]
}

PLAN_ITEMS_WITH_SONGS_RESPONSE = {
    "data": [
        {
            "type": "Item",
            "id": "item-1",
            "attributes": {"title": "Pre-Service", "item_type": "header"},
            "relationships": {"song": {"data": None}},
        },
        {
            "type": "Item",
            "id": "item-2",
            "attributes": {"title": "How Great Is Our God", "item_type": "song"},
            "relationships": {"song": {"data": {"type": "Song", "id": "song-1"}}},
        },
        {
            "type": "Item",
            "id": "item-3",
            "attributes": {"title": "Amazing Grace", "item_type": "song"},
            "relationships": {"song": {"data": {"type": "Song", "id": "song-2"}}},
        },
        {
            "type": "Item",
            "id": "item-4",
            "attributes": {"title": "Announcements", "item_type": "header"},
            "relationships": {},
        },
    ],
    "included": [
        {
            "type": "Song",
            "id": "song-1",
            "attributes": {"title": "How Great Is Our God", "author": "Chris Tomlin"},
        },
        {
            "type": "Song",
            "id": "song-2",
            "attributes": {"title": "Amazing Grace", "author": "John Newton"},
        },
    ],
}

UNAUTHORIZED_RESPONSE = {"errors": [{"status": "401", "title": "Unauthorized"}]}

RATE_LIMIT_HEADERS = {
    "X-PCO-API-Request-Rate-Limit": "100",
    "X-PCO-API-Request-Rate-Count": "85",
}

RATE_LIMIT_EXCEEDED_HEADERS = {
    "Retry-After": "30",
    "X-PCO-API-Request-Rate-Limit": "100",
    "X-PCO-API-Request-Rate-Count": "100",
}
