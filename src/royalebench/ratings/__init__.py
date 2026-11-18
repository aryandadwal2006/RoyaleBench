"""Competitive rating implementations."""

from .glicko2 import Rating, update_rating_period

__all__ = ["Rating", "update_rating_period"]
