"""Tests for CFBD client."""

import os
from unittest.mock import Mock, patch

import pytest

from src.data.cfbd_client import CFBDClient


def test_cfbd_client_init_with_key():
    """Test CFBD client initialization with API key."""
    client = CFBDClient(api_key="test_key")
    assert client.api_key == "test_key"
    assert "Authorization" in client.headers


def test_cfbd_client_init_from_env(monkeypatch):
    """Test CFBD client initialization from environment."""
    monkeypatch.setenv("CFBD_API_KEY", "env_key")
    client = CFBDClient()
    assert client.api_key == "env_key"


def test_cfbd_client_init_no_key():
    """Test CFBD client initialization without key raises error."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="CFBD_API_KEY"):
            CFBDClient()


@patch("src.data.cfbd_client.requests.get")
def test_cfbd_client_get_games(mock_get):
    """Test get_games method."""
    mock_response = Mock()
    mock_response.json.return_value = [
        {"id": 1, "home_team": "Team A", "away_team": "Team B"}
    ]
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    client = CFBDClient(api_key="test_key")
    df = client.get_games(season=2024, week=1)

    assert not df.empty
    assert "home_team" in df.columns
    mock_get.assert_called_once()


@patch("src.data.cfbd_client.requests.get")
def test_cfbd_client_pagination(mock_get):
    """Test pagination handling."""
    mock_response = Mock()
    mock_response.json.return_value = []
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    client = CFBDClient(api_key="test_key")
    df = client.get_games(season=2024)

    assert df.empty
    mock_get.assert_called_once()


