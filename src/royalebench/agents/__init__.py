"""Built-in and adapter-backed RoyaleBench agents."""

from .base import Agent, MatchInfo
from .baselines import HogCycleAgent, NoOpAgent, RandomLegalAgent
from .openai_compatible import OpenAICompatibleAgent
from .subprocess_agent import SubprocessAgent
from .subprocess_agent import AgentProcessError, JsonlSubprocessAgent

__all__ = [
    "Agent",
    "MatchInfo",
    "HogCycleAgent",
    "NoOpAgent",
    "RandomLegalAgent",
    "OpenAICompatibleAgent",
    "AgentProcessError",
    "JsonlSubprocessAgent",
]
