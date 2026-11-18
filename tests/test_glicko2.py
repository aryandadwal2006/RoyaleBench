from __future__ import annotations

import pytest

from royalebench.ratings.glicko2 import PeriodGame, Rating, update_rating, update_rating_period


def test_published_glicko2_example():
    player = Rating(rating=1500, deviation=200, volatility=0.06)
    opponents = {
        "a": Rating(1400, 30, 0.06),
        "b": Rating(1550, 100, 0.06),
        "c": Rating(1700, 300, 0.06),
    }
    updated = update_rating(
        player,
        [PeriodGame("a", 1), PeriodGame("b", 0), PeriodGame("c", 0)],
        opponents,
    )
    assert updated.rating == pytest.approx(1464.06, abs=0.02)
    assert updated.deviation == pytest.approx(151.52, abs=0.02)
    assert updated.volatility == pytest.approx(0.059996, abs=0.00001)


def test_rating_period_uses_frozen_preperiod_ratings():
    ratings = {
        "a": Rating(),
        "b": Rating(),
    }
    games = {
        "a": [PeriodGame("b", 1.0)],
        "b": [PeriodGame("a", 0.0)],
    }
    updated = update_rating_period(ratings, games)
    assert updated["a"].rating > 1500
    assert updated["b"].rating < 1500
    assert updated["a"].rating == pytest.approx(1500 + (1500 - updated["b"].rating), abs=1e-6)


def test_missing_opponent_is_rejected():
    with pytest.raises(KeyError, match="missing pre-period rating"):
        update_rating(Rating(), [PeriodGame("missing", 1.0)], {})
