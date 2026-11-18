from __future__ import annotations

from royalebench.agents.baselines import HogCycleAgent, NoOpAgent, RandomLegalAgent


def observation():
    return {
        "own": {
            "hand": [
                {"slot": 0, "card": "HogRider", "cost_elixir": 4},
                {"slot": 1, "card": "Cannon", "cost_elixir": 3},
                {"slot": 2, "card": "IceSpirit", "cost_elixir": 1},
                {"slot": 3, "card": "Skeletons", "cost_elixir": 1},
            ]
        },
        "opponent": {
            "towers": {
                "enemy_left": {"hp": 1500},
                "enemy_right": {"hp": 1800},
            }
        },
        "entities": [],
        "legal_actions": {
            "playable_slots": [0, 1, 2, 3],
            "ability_slots": [],
        },
    }


def test_noop_agent_waits():
    agent = NoOpAgent()
    agent.reset({"seed": 1, "seat": 0})
    assert agent.act(observation()) == {"schema": "royalebench.action.v1", "type": "wait"}


def test_random_agent_returns_well_formed_action():
    agent = RandomLegalAgent(wait_probability=0.0)
    agent.reset({"seed": 123, "seat": 1})
    action = agent.act(observation())
    assert action["schema"] == "royalebench.action.v1"
    assert action["type"] in {"play", "ability"}
    if action["type"] == "play":
        assert action["expected_card"] in {"HogRider", "Cannon", "IceSpirit", "Skeletons"}
        assert action["x_tile"] % 1 == 0.5
        assert action["y_tile"] % 1 == 0.5


def test_hog_cycle_agent_uses_hog_at_bridge_when_available():
    agent = HogCycleAgent()
    action = agent.act(observation())
    assert action == {
        "schema": "royalebench.action.v1",
        "type": "play",
        "hand_slot": 0,
        "expected_card": "HogRider",
        "x_tile": 3.5,
        "y_tile": 14.5,
    }
