"""Tests for Odds API client."""

import os
from unittest.mock import Mock, patch

import pytest

from src.data.odds.odds_api import OddsAPIClient, OddsQuote


def test_odds_api_client_init_with_key():
    """Test Odds API client initialization with API key."""
    client = OddsAPIClient(api_key="test_key")
    assert client.api_key == "test_key"
    assert client.region == "us"


def test_odds_api_client_init_from_env(monkeypatch):
    """Test Odds API client initialization from environment."""
    monkeypatch.setenv("ODDS_API_KEY", "env_key")
    client = OddsAPIClient()
    assert client.api_key == "env_key"


def test_odds_api_client_init_no_key():
    """Test Odds API client initialization without key raises error."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="ODDS_API_KEY"):
            OddsAPIClient()


@patch("src.data.odds.odds_api.requests.get")
def test_odds_api_get_current_odds(mock_get):
    """Test get_current_odds method."""
    mock_response = Mock()
    mock_response.json.return_value = [
        {
            "home_team": "Team A",
            "away_team": "Team B",
            "bookmakers": [
                {
                    "key": "book1",
                    "markets": [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Team A", "price": -110},
                                {"name": "Team B", "price": -110},
                            ],
                        }
                    ],
                }
            ],
        }
    ]
    mock_response.headers = {"x-requests-remaining": "100", "x-requests-used": "1"}
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    client = OddsAPIClient(api_key="test_key")

    def mapper(name):
        return name

    quotes = client.get_current_odds(team_name_mapper=mapper)

    assert len(quotes) > 0
    assert isinstance(quotes[0], OddsQuote)
    mock_get.assert_called_once()


def test_odds_quote_dataclass():
    """Test OddsQuote dataclass."""
    quote = OddsQuote(
        season=2024,
        week=1,
        home_team="Team A",
        away_team="Team B",
        bookmaker="book1",
        market="h2h",
        price_home=-110,
        price_away=-110,
    )

    assert quote.season == 2024
    assert quote.week == 1
    assert quote.home_team == "Team A"


