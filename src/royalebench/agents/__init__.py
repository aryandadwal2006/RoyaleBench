"""Built-in policies and execution adapters for RoyaleBench agents."""

from .base import Agent, MatchInfo
from .baselines import HogCycleAgent, NoOpAgent, RandomLegalAgent
from .openai_compatible import OpenAICompatibleAgent
from .subprocess_agent import SubprocessAgent

__all__ = [
    "Agent",
    "MatchInfo",
    "HogCycleAgent",
    "NoOpAgent",
    "RandomLegalAgent",
    "OpenAICompatibleAgent",
    "SubprocessAgent",
]
