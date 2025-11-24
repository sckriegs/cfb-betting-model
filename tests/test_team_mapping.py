"""Tests for team name mapping."""

from src.data.team_mapping import to_canonical


def test_to_canonical_exact_match():
    """Test exact match mapping."""
    assert to_canonical("Ole Miss") == "Mississippi"
    assert to_canonical("UConn") == "Connecticut"
    assert to_canonical("LA Tech") == "Louisiana Tech"


def test_to_canonical_case_insensitive():
    """Test case-insensitive matching."""
    assert to_canonical("ole miss") == "Mississippi"
    assert to_canonical("UCONN") == "Connecticut"


def test_to_canonical_no_mapping():
    """Test that unmapped names return as-is."""
    assert to_canonical("Alabama") == "Alabama"
    assert to_canonical("Unknown Team") == "Unknown Team"


def test_to_canonical_empty():
    """Test empty string handling."""
    assert to_canonical("") == ""
    assert to_canonical(None) == None  # noqa: E711


