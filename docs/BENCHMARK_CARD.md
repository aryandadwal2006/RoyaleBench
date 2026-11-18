# RoyaleBench v1 benchmark card

**Document status:** Implementation description, pending final local engine acceptance.  
**Benchmark version:** v1.0 candidate  
**Canonical simulator:** CRForge commit `fa5959055c590a493d62c8dbc804e602832d08a6`  
**Game-data target:** 16.635.8  
**Last updated:** 2026-11-18

## Summary

RoyaleBench is an offline benchmark for comparing autonomous agents in a fixed, Clash Royale-style 1v1 environment. It standardizes the simulator, deck, player-visible observations, actions, decision cadence, tournament pairing and trajectory export. It is not an automation tool for live Clash Royale accounts.

The intended users are researchers evaluating scripted policies, reinforcement-learning agents, model-based controllers and LLM-driven agents under the same structured-state interface.

## Task

Each agent controls one seat in a two-player battle. At each decision point, it receives its own ObservationV1 and returns one ActionV1. The engine remains authoritative for action legality, placement search, command delay and game outcomes.

V1 fixes both seats to the same Hog 2.6 deck and equal card/tower levels. The exact deck ordering, levels, engine build and data hash are recorded in the match manifest.

## Tracks and outputs

- **Competitive structured-state track:** paused-clock agent decisions at the `fast-250ms-v1` (5 engine ticks) or `llm-api-1s-v1` (20 engine ticks) cadence. Ratings are kept separate by cadence.
- **Forecasting evaluation:** action-conditioned future ObservationV1 prediction at multiple decision-interval horizons. The initial persistence baseline is a sanity reference, not a learned model.
- **Trajectory data:** compressed train/validation/test JSONL shards, split by simulator seed group, with a dataset manifest and SHA-256 hashes.

The competitive leaderboard uses match win/draw/loss outcomes and Glicko-2. Forecast metrics are not combined with competitive ratings.

## Observation and action contract

The structured observation is built from CRForge's seat-visible observation arrays. It contains the agent's own hand/deck/elixir, public board state, towers, visible entities and effects, public opponent plays, legal action masks and opponent estimates derived from public information. The benchmark does not intentionally expose the opponent's true hand, next card or privileged simulator state.

Actions are wait, play a card from one of four hand slots at an 18 x 32 tile-centre coordinate, or use a supported ability button. The v1 fixed deck does not rely on champion or evolution abilities. The native CRForge PlayerCommands path controls placement and its delay.

## Evaluation protocol

Each pair of agents plays both seat assignments for each configured seed. Both agents decide concurrently while the simulation clock is paused. Each decision has a shared watchdog deadline. Agent failures, invalid actions and engine faults are recorded separately from completed game outcomes; failed/void games are not converted into strategic losses.

The tournament manifest records the schedule, seeds, cadence, rating settings, engine fingerprints, per-match manifest hashes and hashes/sizes for match result and trajectory artifacts.

## Intended use

Appropriate uses include:
- comparing policies under a fixed simulator and deck;
- testing whether an LLM or learned controller can use structured observations;
- measuring decision-time latency separately from strategic strength;
- generating action/state trajectories for representation learning and world-model forecasting;
- testing action-conditioned future-state prediction on held-out seed groups.

## Out-of-scope uses

V1 does not establish:
- strength in the official live Clash Royale client;
- human-level play or general game intelligence;
- performance across arbitrary decks, game versions or card mechanics;
- visual-agent performance from screenshots;
- real-time performance under a wall-clock competition;
- universal simulator fidelity for every card or mechanic;
- a public secure sandbox for untrusted third-party code.

External pretrained agents are not official leaderboard entries until licensing, checkpoint availability, observation/action compatibility and reproducibility have been verified.

## Known limitations and validation status

- CRForge is a deterministic offline engine with a bounded conformance/fidelity scope. Results are conditional on its pinned commit and locally obtained game data.
- The engine's game tables are not distributed by RoyaleBench. Users must obtain/build them through the documented upstream process.
- The subprocess adapter restricts inherited environment variables and enforces timeouts, but is not an OS/container security boundary.
- The opponent elixir and card-cycle estimates are derived from public observations and engine accounting; their edge cases require further differential testing.
- Forecasting metrics currently cover visible tower HP, elixir, entity-type counts and entity-count error. Stable entity identity, movement trajectories and event-timing metrics are not yet implemented.
- Final local Windows headless acceptance against the user's installed CRForge build remains outstanding. The desktop visualizer smoke test does not prove headless adapter correctness.
- The upstream CRForge test failures previously observed by the project owner have not yet been reconciled with the exact test log.

## Reproducibility

A result should be interpreted together with:
- RoyaleBench commit;
- CRForge commit and schema version;
- game-data version and content SHA-256;
- v1 config, deck, levels, cadence and seed;
- agent source/model identifiers and declared configuration;
- tournament manifest and per-match manifests;
- dataset manifest and forecast report, where applicable.

Do not compare ratings across different engine/data fingerprints or cadence profiles.

## Release status

This is a benchmark card for the v1 candidate, not a claim that final acceptance has passed. The release is ready for paper-grade evaluation only after the local integrated validation script succeeds and the remaining FAIR-observation, simulator-fidelity and opponent-estimation audits are documented.
