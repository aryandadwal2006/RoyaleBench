# RoyaleBench v1 benchmark card

**Document status:** v1 candidate specification; final headless adapter acceptance remains pending.  
**Benchmark version:** v1.0 candidate  
**Canonical simulator:** CRForge commit `fa5959055c590a493d62c8dbc804e602832d08a6`  
**Game-data target:** 16.635.8  
**Game-data content SHA:** `062a11e0500c03cc041f123413b1ef1846b539a4`  
**Last updated:** 2026-11-18

## Summary

RoyaleBench is an offline benchmark for comparing autonomous agents in a fixed, Clash Royale-style 1v1 environment. It standardizes the simulator, deck, player-visible observations, actions, decision cadence, tournament pairing and trajectory export. It is not an automation tool for live Clash Royale accounts.

The intended users are researchers evaluating scripted policies, reinforcement-learning agents, model-based controllers and LLM-driven agents under the same structured-state interface.

## Task

Each agent controls one seat in a two-player battle. At each decision point, it receives its own ObservationV1 and returns one ActionV1. The engine remains authoritative for action legality, placement search, command delay and game outcomes.

V1 fixes both seats to the exact same ordered Hog 2.6 deck, card/tower level 11, CRForge commit `fa5959055c590a493d62c8dbc804e602832d08a6`, and game-data content SHA `062a11e0500c03cc041f123413b1ef1846b539a4`. Startup rejects any source/data/configuration drift.

## Tracks and outputs

- **Competitive structured-state track:** paused-clock agent decisions at the `fast-250ms-v1` (5 engine ticks) or `llm-api-1s-v1` (20 engine ticks) simulation cadence. These are action/observation frequencies, not inference-time budgets. Ratings are kept separate by cadence.
- **Forecasting evaluation:** action-conditioned future ObservationV1 prediction at multiple decision-interval horizons. The initial persistence baseline is a sanity reference, not a learned model.
- **Trajectory data:** compressed train/validation/test JSONL shards, split by simulator seed group, with a dataset manifest and SHA-256 hashes.

The competitive leaderboard uses match win/draw/loss outcomes and Glicko-2. Forecast metrics are not combined with competitive ratings.

## Observation and action contract

The structured observation is built from CRForge's seat-visible observation arrays. It contains the agent's own hand/deck/elixir, public board state, towers, visible entities and effects, public opponent plays, legal action masks and opponent estimates derived from public information. The benchmark does not intentionally expose the opponent's true hand, next card or privileged simulator state.

Actions are wait, play a card from one of four hand slots at an 18 x 32 tile-centre coordinate, or use a supported ability button. The v1 fixed deck does not rely on champion or evolution abilities. The native CRForge PlayerCommands path controls placement and its delay.

## Evaluation protocol

Each pair of agents plays both seat assignments for each configured seed. Both agents decide concurrently while the simulation clock is paused. Each decision has a shared watchdog deadline. Agent failures, invalid actions and engine faults are recorded separately from completed game outcomes; failed/void games are not converted into strategic losses. A match is voided if either seat's observation reports entity overflow, because the state supplied to the agent would be incomplete.

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
- Opponent elixir is CRForge's seat-side `ElixirCount` accounting, derived from what that seat can see rather than the opponent's hidden elixir field. CRForge documents a possible source of drift from champion ability refunds not shown to the opponent. The fixed Hog 2.6 v1 deck has no champion, so that path is outside the v1 deck. A native v1-specific differential test is included in the acceptance suite. Public opponent card-cycle inference remains bounded by what the play ledger has revealed.
- Forecasting metrics cover visible tower HP, own/public-opponent elixir, entity-type counts, stable seat-local entity IDs, matched-entity position and visible HP errors, and entity-count error. Public event-timing metrics remain future work.
- Runtime guards verify the actual CRForge source commit, game-data version and content SHA, effective cadence, levels, tick limit, mask/id versions and 20-tick PlayerCommands delay. Reset-time guards verify the actual mirrored deck, card levels, equal tower HP and initial public-elixir accounting.
- In the 2026-11-18 Windows partial run, the pinned CRForge `:env:test` Gradle task completed successfully. RoyaleBench's Python suite reported 114 passed and 3 skipped; the skipped cases were the three native adapter tests in `tests/test_crforge_native.py`, because the `env/build/install/env` runtime distribution had not been built. The headless tournament then stopped before starting a match because the runtime JARs were absent.
- The desktop visualizer smoke test and a successful upstream Gradle test task do not by themselves prove headless adapter correctness. Final acceptance requires the Python native tests to execute, both headless tournaments to complete, and dataset/forecast evaluation to finish.


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
