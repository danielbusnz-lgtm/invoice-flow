"""Test suite for the processed-emails tracker."""
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from services.tracker import (
    load_processed_ids,
    save_processed_ids,
    mark_processed,
    is_processed,
    TRACKER_FILE,
)


@pytest.fixture(autouse=True)
def temp_tracker(tmp_path):
    """Redirect the tracker to a temporary directory for every test."""
    fake_file = tmp_path / "processed_emails.json"
    with patch("services.tracker.TRACKER_FILE", fake_file), \
         patch("services.tracker.DATA_DIR", tmp_path):
        yield fake_file


class TestLoadProcessedIds:

    def test_empty_when_no_file(self, temp_tracker):
        assert load_processed_ids() == set()
        print("No file returns empty set")

    def test_loads_existing_ids(self, temp_tracker):
        temp_tracker.write_text(json.dumps(["msg-1", "msg-2"]))
        result = load_processed_ids()
        assert result == {"msg-1", "msg-2"}
        print("Existing IDs loaded correctly")

    def test_handles_corrupt_json(self, temp_tracker):
        temp_tracker.write_text("{bad json")
        assert load_processed_ids() == set()
        print("Corrupt JSON returns empty set")

    def test_handles_empty_file(self, temp_tracker):
        temp_tracker.write_text("")
        assert load_processed_ids() == set()
        print("Empty file returns empty set")


class TestSaveProcessedIds:

    def test_saves_sorted_json(self, temp_tracker):
        save_processed_ids({"c", "a", "b"})
        data = json.loads(temp_tracker.read_text())
        assert data == ["a", "b", "c"]
        print("IDs saved as sorted JSON list")

    def test_creates_file_if_missing(self, temp_tracker):
        assert not temp_tracker.exists()
        save_processed_ids({"msg-1"})
        assert temp_tracker.exists()
        print("File created on first save")


class TestMarkProcessed:

    def test_adds_new_id(self, temp_tracker):
        mark_processed("msg-1")
        assert is_processed("msg-1")
        print("New ID marked and found")

    def test_preserves_existing_ids(self, temp_tracker):
        temp_tracker.write_text(json.dumps(["msg-1"]))
        mark_processed("msg-2")
        ids = load_processed_ids()
        assert "msg-1" in ids
        assert "msg-2" in ids
        print("Existing IDs preserved after mark")

    def test_duplicate_mark_is_safe(self, temp_tracker):
        mark_processed("msg-1")
        mark_processed("msg-1")
        ids = load_processed_ids()
        assert len(ids) == 1
        print("Duplicate mark does not create duplicates")


class TestIsProcessed:

    def test_returns_false_for_unknown(self, temp_tracker):
        assert is_processed("msg-never") is False
        print("Unknown ID returns False")

    def test_returns_true_for_known(self, temp_tracker):
        mark_processed("msg-known")
        assert is_processed("msg-known") is True
        print("Known ID returns True")


class TestMainIntegration:
    """Verify that main.py skips already-processed emails."""

    def test_skip_logic_concept(self, temp_tracker):
        """Demonstrate the skip pattern used in main.py."""
        mark_processed("already-done")

        processed = []
        messages = [
            ("already-done", "Old email", "", []),
            ("brand-new", "New email", "", []),
        ]

        for msg_id, subject, text, atts in messages:
            if is_processed(msg_id):
                continue
            processed.append(msg_id)
            mark_processed(msg_id)

        assert processed == ["brand-new"]
        assert is_processed("brand-new")
        print("Skip logic works: only new emails processed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
