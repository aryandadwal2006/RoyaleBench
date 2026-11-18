"""Glicko-2 rating updates using frozen pre-period opponent ratings."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

_SCALE = 173.7178
_PI2 = math.pi * math.pi


@dataclass(frozen=True, slots=True)
class Rating:
    rating: float = 1500.0
    deviation: float = 350.0
    volatility: float = 0.06

    def __post_init__(self) -> None:
        if not math.isfinite(self.rating):
            raise ValueError("rating must be finite")
        if not math.isfinite(self.deviation) or self.deviation <= 0:
            raise ValueError("rating deviation must be finite and positive")
        if not math.isfinite(self.volatility) or self.volatility <= 0:
            raise ValueError("volatility must be finite and positive")


@dataclass(frozen=True, slots=True)
class PeriodGame:
    opponent: str
    score: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("game score must be in [0, 1]")


def _g(phi: float) -> float:
    return 1.0 / math.sqrt(1.0 + 3.0 * phi * phi / _PI2)


def _expected(mu: float, opponent_mu: float, opponent_phi: float) -> float:
    exponent = -_g(opponent_phi) * (mu - opponent_mu)
    if exponent >= 700.0:
        return 0.0
    if exponent <= -700.0:
        return 1.0
    return 1.0 / (1.0 + math.exp(exponent))


def _volatility(
    phi: float,
    sigma: float,
    delta: float,
    variance: float,
    tau: float,
    epsilon: float,
) -> float:
    a = math.log(sigma * sigma)

    def f(x: float) -> float:
        exp_x = math.exp(x)
        numerator = exp_x * (delta * delta - phi * phi - variance - exp_x)
        denominator = 2.0 * (phi * phi + variance + exp_x) ** 2
        return numerator / denominator - (x - a) / (tau * tau)

    A = a
    if delta * delta > phi * phi + variance:
        B = math.log(delta * delta - phi * phi - variance)
    else:
        k = 1
        B = a - k * tau
        while f(B) < 0.0:
            k += 1
            B = a - k * tau
            if k > 10_000:
                raise ArithmeticError("Glicko-2 volatility bracket did not converge")

    fA = f(A)
    fB = f(B)
    iterations = 0
    while abs(B - A) > epsilon:
        denominator = fB - fA
        if denominator == 0:
            break
        C = A + (A - B) * fA / denominator
        fC = f(C)
        if fC * fB <= 0:
            A, fA = B, fB
        else:
            fA /= 2.0
        B, fB = C, fC
        iterations += 1
        if iterations > 10_000:
            raise ArithmeticError("Glicko-2 volatility iteration did not converge")
    return math.exp(A / 2.0)


def update_rating(
    player: Rating,
    games: Sequence[PeriodGame],
    opponent_ratings: Mapping[str, Rating],
    *,
    tau: float = 0.5,
    epsilon: float = 1e-6,
) -> Rating:
    """Update one player's rating once at the end of a rating period."""
    if tau <= 0 or epsilon <= 0:
        raise ValueError("tau and epsilon must be positive")
    if not games:
        return player

    mu = (player.rating - 1500.0) / _SCALE
    phi = player.deviation / _SCALE
    opponents: list[tuple[float, float, float]] = []
    for game in games:
        if game.opponent not in opponent_ratings:
            raise KeyError(f"missing pre-period rating for opponent {game.opponent!r}")
        opponent = opponent_ratings[game.opponent]
        opponents.append(
            (
                (opponent.rating - 1500.0) / _SCALE,
                opponent.deviation / _SCALE,
                game.score,
            )
        )

    variance_inverse = 0.0
    score_sum = 0.0
    for opponent_mu, opponent_phi, score in opponents:
        g_value = _g(opponent_phi)
        expected = _expected(mu, opponent_mu, opponent_phi)
        variance_inverse += g_value * g_value * expected * (1.0 - expected)
        score_sum += g_value * (score - expected)

    if variance_inverse <= 0.0:
        return player
    variance = 1.0 / variance_inverse
    delta = variance * score_sum
    sigma_prime = _volatility(phi, player.volatility, delta, variance, tau, epsilon)
    phi_star = math.sqrt(phi * phi + sigma_prime * sigma_prime)
    phi_prime = 1.0 / math.sqrt(1.0 / (phi_star * phi_star) + 1.0 / variance)
    mu_prime = mu + phi_prime * phi_prime * score_sum

    return Rating(
        rating=1500.0 + _SCALE * mu_prime,
        deviation=_SCALE * phi_prime,
        volatility=sigma_prime,
    )


def update_rating_period(
    ratings: Mapping[str, Rating],
    games: Mapping[str, Sequence[PeriodGame]],
    *,
    tau: float = 0.5,
    epsilon: float = 1e-6,
) -> dict[str, Rating]:
    """Batch-update all players against the same frozen pre-period rating table."""
    snapshot = dict(ratings)
    updated = dict(snapshot)
    for player, player_games in games.items():
        if player not in snapshot:
            raise KeyError(f"unknown player {player!r}")
        updated[player] = update_rating(
            snapshot[player],
            player_games,
            snapshot,
            tau=tau,
            epsilon=epsilon,
        )
    return updated
