from datetime import UTC, datetime, timedelta

from qpcr_assay_check.ncbi.cache import Cache, content_key


def test_content_key_is_stable_and_order_insensitive():
    assert content_key({"a": 1, "b": [1, 2]}) == content_key({"b": [1, 2], "a": 1})
    assert content_key({"a": 1}) != content_key({"a": 2})
    assert len(content_key({})) == 64


def test_round_trip(tmp_path):
    c = Cache(tmp_path)
    assert c.get("blast", "ab" * 32, ttl_days=7) is None
    c.put("blast", "ab" * 32, "hello ✓")
    assert c.get("blast", "ab" * 32, ttl_days=7) == "hello ✓"
    assert c.get("other", "ab" * 32, ttl_days=7) is None  # kinds are separate


def test_ttl_expiry_and_no_expiry(tmp_path):
    clock = {"t": datetime(2026, 9, 1, tzinfo=UTC)}
    c = Cache(tmp_path, now=lambda: clock["t"])
    c.put("blast", "cd" * 32, "x")
    clock["t"] += timedelta(days=6)
    assert c.get("blast", "cd" * 32, ttl_days=7) == "x"
    clock["t"] += timedelta(days=2)
    assert c.get("blast", "cd" * 32, ttl_days=7) is None  # last year's answer is never served
    assert c.get("blast", "cd" * 32, ttl_days=None) == "x"  # immutable data: no expiry


def test_corrupt_entries_are_treated_as_misses(tmp_path):
    c = Cache(tmp_path)
    path = c.put("blast", "ef" * 32, "x")
    path.write_bytes(b"not gzip at all")
    assert c.get("blast", "ef" * 32, ttl_days=7) is None


def test_no_temporary_files_are_left_behind(tmp_path):
    Cache(tmp_path).put("blast", "01" * 32, "x")
    assert not list(tmp_path.rglob("*.tmp"))
