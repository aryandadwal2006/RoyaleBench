# RoyaleBench

**A reproducible competitive benchmark for AI agents in Clash Royale-like real-time battles.**

RoyaleBench provides the game environment, fair observations, opponent-memory bookkeeping, action execution, match scheduling, latency measurement, replay logging, and rankings. Researchers bring the agent: an LLM/VLM, learned world model plus planner, RL policy, scripted policy, or another system that implements the documented adapter.

## Design status

This repository is at the architecture and bootstrap stage. The initial design is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). Decisions about upstream code and licensing are in [docs/REUSE_PLAN.md](docs/REUSE_PLAN.md). The implementation sequence is in [docs/ROADMAP.md](docs/ROADMAP.md).

**Proposed v1 choices**
- One canonical battle engine: [crforge](https://github.com/voonhous/crforge), pinned as an upstream submodule.
- Fixed, mirrored decks for the initial competition; deck-building is out of scope for v1.
- Two observation modalities: structured player-visible state and rendered pixels. They receive separate rankings.
- One versioned action protocol, with native engine placement semantics and an explicit placement-resolution contract.
- A common deterministic public-memory layer for opponent elixir and card-cycle deductions.
- Separate strategic-strength (lockstep) and real-time (wall-clock) evaluations.
- Match outcomes drive agent ratings. Prediction accuracy is reported separately for world models.

## Repository layout

See [the architecture document](docs/ARCHITECTURE.md). The intended layout separates the engine adapter, observation/memory layer, agent SDK, tournament runner, evaluation, visualizer integration, schemas, and optional human interface.

## Upstream references

The upstream implementations are not silently copied into RoyaleBench's own source tree. They are pinned under third_party/upstream as Git submodules so their exact source and licenses remain inspectable. See [third_party/README.md](third_party/README.md).

## Safety and scope

RoyaleBench targets offline simulation and human-operated play in its own research interface. It is not an automation client for official Clash Royale accounts, and it will not automate, log into, or control live Supercell accounts.

## Current limitations

- The engine must pass a local acceptance test before being declared the benchmark's supported runtime.
- Higher-resolution / continuous placement is a proposed extension, not an existing crforge feature.
- The shared observation and memory protocol still needs implementation and tests against the canonical engine.
- Game data tables and original game assets are not bundled. Their provenance and redistribution permissions require separate review.
