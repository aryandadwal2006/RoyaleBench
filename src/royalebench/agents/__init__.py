"""Built-in RoyaleBench agents."""

from .base import Agent, MatchInfo
from .baselines import HogCycleAgent, NoOpAgent, RandomLegalAgent
from .openai_compatible import OpenAICompatibleAgent

__all__ = [
    "Agent",
    "MatchInfo",
    "HogCycleAgent",
    "NoOpAgent",
    "RandomLegalAgent",
    "OpenAICompatibleAgent",
]
