"""Unit tests for the VK Search WS controller helpers.

These cover the pure functions responsible for:
- query normalization (used as the Redis cache key),
- extracting group ids from the raw VK ``search.getHints`` response,
- annotating items with ``in_db`` / ``db_group_id`` after the DB lookup.

The full WebSocket flow (debounce + cache + enrich) is best exercised in
integration tests with a running Redis; here we validate the building
blocks and guarantee behaviour doesn't regress silently.
"""

from src.Containers.AppSection.VkParser.UI.API.Controllers.VkSearchWsController import (
    MAX_NORMALIZED_Q_LEN,
    _annotate_items_with_in_db,
    _extract_group_ids,
    _normalize_q,
)


class TestNormalizeQuery:
    def test_strips_whitespace(self):
        assert _normalize_q("  Lentach  ") == "lentach"

    def test_lowercases(self):
        assert _normalize_q("LENTACH") == "lentach"

    def test_truncates_long_input(self):
        long_q = "a" * 200
        assert len(_normalize_q(long_q)) == MAX_NORMALIZED_Q_LEN


class TestExtractGroupIds:
    def test_pulls_group_type_hits(self):
        items = [
            {"id": 123, "type": "group", "screen_name": "lentach"},
            {"id": 456, "type": "page", "screen_name": "mdk"},
        ]
        assert _extract_group_ids(items) == [123, 456]

    def test_skips_negative_ids(self):
        items = [{"id": -1, "type": "group"}, {"id": 0, "type": "group"}]
        assert _extract_group_ids(items) == []

    def test_skips_non_dict_items(self):
        assert _extract_group_ids([None, 123, "oops"]) == []  # type: ignore[list-item]

    def test_ignores_profile_hits(self):
        # VK hints can return user profiles alongside groups — we only care
        # about groups/pages for the "in DB" marker.
        items = [{"id": 999, "type": "profile"}]
        assert _extract_group_ids(items) == []


class TestAnnotateItemsWithInDb:
    def test_marks_present_ids(self):
        items = [{"id": 1, "type": "group"}, {"id": 2, "type": "group"}]
        presence = {1: True, 2: False}
        result = _annotate_items_with_in_db(items, presence)
        assert result[0]["in_db"] is True
        assert result[0]["db_group_id"] == 1
        assert result[1]["in_db"] is False
        assert result[1]["db_group_id"] is None

    def test_unknown_id_defaults_to_not_in_db(self):
        items = [{"id": 42, "type": "group"}]
        assert _annotate_items_with_in_db(items, {})[0]["in_db"] is False

    def test_preserves_original_fields(self):
        items = [{"id": 1, "name": "Lentach", "screen_name": "lentach"}]
        result = _annotate_items_with_in_db(items, {1: True})
        assert result[0]["name"] == "Lentach"
        assert result[0]["screen_name"] == "lentach"

    def test_skips_non_dict_items(self):
        result = _annotate_items_with_in_db(["nope"], {})  # type: ignore[list-item]
        assert result == ["nope"]
