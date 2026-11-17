# Implementation Roadmap

**Status:** Planning/bootstrap. No engine adapter, match runner or agent SDK is implemented yet.

The roadmap is ordered to reduce research risk. Do not build LLM provider integrations or world-model planners before the environment, visibility and action semantics are tested.

## Phase 0 — Repository and upstream bootstrap

- [x] Create repository design README.
- [x] Write architecture specification.
- [x] Write upstream reuse/licensing plan.
- [x] Pin upstream source trees as Git submodules.
- [x] Add third-party notices and a reproducible local setup guide.
- [x] Add Python package metadata, formatting, typing and CI.
- [x] Add architecture decision records for engine, action resolution, observation cadence and latency modes.

**Exit gate:** a clean clone with recursive submodules can show the exact upstream source revisions used by the design.

### Protocol bootstrap (completed ahead of Phase 1)

- [x] Add versioned ActionV1 JSON Schema.
- [x] Add request-bound AgentResponseV1 envelope.
- [x] Add typed Python parsing/validation for wait, play and ability actions.
- [x] Validate tile-centre and half-tile action coordinates without silently snapping.
- [x] Add request ID, decision ID and observation-hash checks to reject stale responses.
- [x] Add unit tests and a GitHub Actions test/lint workflow.

The half-tile code validates a proposed protocol resolution only. It does not yet extend crforge's engine action schema or masks.

## Phase 1 — Engine acceptance and human-play prototype

- [ ] Build crforge with its documented Java 21 toolchain.
- [ ] Build one selected game-data version locally; record the version and content hash.
- [ ] Run all upstream tests and the relevant conformance suite.
- [ ] Verify every card/mechanic in the first fixed deck.
- [ ] Run the existing desktop visualizer and play both seats manually.
- [ ] Test identical seed/action replay determinism.
- [ ] Test player-command delay, pending elixir reservation, native placement and refusal reasons.
- [ ] Test both seat observations for hidden-state leakage.
- [ ] Write RoyaleBench's engine acceptance report.

**Exit gate:** a reproducible local human-vs-human simulated match, with saved replay, exact engine/data provenance and documented unsupported cases.

## Phase 2 — Canonical match runner and protocol

- [ ] Implement a Python engine adapter around the crforge environment.
- [ ] Define JSON Schemas for ObservationV1, ActionV1, AgentMetadataV1 and MatchManifestV1.
- [ ] Implement typed Python dataclasses and validators from those schemas.
- [ ] Implement one fixed mirrored deck, equal levels and deterministic seed derivation.
- [ ] Implement a two-seat lockstep scheduler.
- [ ] Implement action parsing, native command execution and requested/actual placement logging.
- [ ] Implement match termination, draw, engine-fault and unsupported-action handling.
- [ ] Save replays and per-decision logs.
- [ ] Add a no-op agent and random-legal agent as protocol tests.

**Exit gate:** two independently running baseline agents complete paired games; identical configurations reproduce the same engine/action/result logs.

## Phase 3 — Fair observation and public memory

- [ ] Define the FAIR observation field registry.
- [ ] Map crforge seat schema fields to the canonical RoyaleBench schema.
- [ ] Implement visible event extraction and a bounded recent-event ledger.
- [ ] Implement opponent-elixir accounting from public plays and integer tick rules.
- [ ] Implement public card-cycle/possible-hand/queue inference for the mirrored deck.
- [ ] Include exactness/uncertainty flags and known unsupported income/refund cases.
- [ ] Add ability/evolution-cycle bookkeeping only for mechanics covered by tests.
- [ ] Port minimal RoyaleGym memory logic with attribution and an engine-specific adapter.
- [ ] Add differential tests: compare public-memory values to engine truth in tests only, then assert the agent packet never contains that truth.
- [ ] Add two-seat mirror tests and deliberate leak tests.

**Exit gate:** every observation field has a documented source class (visible, inferred, uncertain or privileged); tests demonstrate that no privileged field reaches the FAIR packet.

## Phase 4 — Placement precision and timing

- [ ] Establish the existing crforge 18 × 32 tile-centre baseline.
- [ ] Measure actual placement resolution needed for tactical cases.
- [ ] Prototype 36 × 64 half-tile actions by adapting crforge's action schema/mask, using native PlayerCommands placement.
- [ ] Compare tile-centre, half-tile and fixed-point actions on a fixed battery of placement scenarios.
- [ ] Verify coordinate transforms for both seats.
- [ ] Verify requested point, snapped point, native landing point, pending command and execution tick.
- [ ] Test no-deploy areas, bridges, tower proximity, spells, buildings and special placement rules.
- [ ] Version the selected action resolution. Do not mix action resolutions in one rating.

**Exit gate:** action-resolution tests establish the exact meaning of every coordinate and show identical semantics for both seats.

## Phase 5 — Agent SDK and execution backends

- [ ] Publish a minimal Python Agent protocol.
- [ ] Implement a persistent local subprocess runner.
- [ ] Implement a container runner with resource limits and a restricted filesystem.
- [ ] Implement an HTTP/WebSocket remote-agent adapter.
- [ ] Implement concurrent requests for both seats.
- [ ] Implement structured-output validation and malformed-response handling.
- [ ] Implement agent reset/close lifecycle and per-match memory isolation.
- [ ] Implement a reference scripted agent and one baseline recurrent/RL agent.
- [ ] Publish a small external-lab example agent that can play a local match without modifying RoyaleBench.

**Exit gate:** an outside lab can clone RoyaleBench, implement the SDK, and enter a match without changing the engine or tournament code.

## Phase 6 — Latency protocols

### Strategic-strength / paused-clock
- [ ] Freeze the game at a decision tick.
- [ ] Dispatch both agent requests concurrently.
- [ ] Record response timestamps and wait under a published operational watchdog.
- [ ] Resume the engine only when both actions or watchdog outcomes are resolved.
- [ ] Count timeouts and apply the published no-action/forfeit rule.
- [ ] Verify game ticks and decision counts are identical regardless of agent response duration.

### Real-time / wall-clock
- [ ] Advance engine on a monotonic wall-clock schedule.
- [ ] Permit at most one outstanding request per agent.
- [ ] Timestamp observations and responses.
- [ ] Discard stale actions and record deadline misses.
- [ ] Verify that slow agents do not pause or backdate the game.

- [ ] Publish P50/P95/P99 latency, timeout rate, deadline misses, effective actions per game-minute, provider/model ID, token/cost telemetry and planner breakdown.

**Exit gate:** tests with artificial 50 ms, 500 ms, 2 s and delayed responses prove the two modes have the documented behaviour.

## Phase 7 — Tournament and scoring

- [ ] Implement fixed match schedules and hidden evaluation seeds.
- [ ] Implement paired side swaps.
- [ ] Implement baseline opponent pool: no-op, random legal, simple defensive, simple aggressive and frozen learned policy.
- [ ] Implement Glicko-2 with the initial parameters and rating-period policy in ADR-0009.
- [ ] Report W/D/L, uncertainty, crown differential, opponent-specific results and invalid/timeouts.
- [ ] Keep separate modality, latency and action-resolution leaderboards.
- [ ] Add run manifests, replay hashes and signed result bundles.

**Exit gate:** tournament results can be regenerated from manifests; leaderboard rankings include uncertainty and are not based on a single raw win percentage.

## Phase 8 — World-model and model-based-agent benchmark

- [ ] Define a predictor API: context/history + candidate action sequence + horizon -> predicted states/events or predicted frames.
- [ ] Define a distinct opponent-response prediction API.
- [ ] Build match-level train/validation/hidden-test splits.
- [ ] Implement open-loop forecasting metrics and multi-horizon evaluation.
- [ ] Implement paired counterfactual forks from the same initial state.
- [ ] Implement a fixed MPC candidate generator and model-query budget.
- [ ] Compare MLP, RSSM, transformer and JEPA-style predictors where available.
- [ ] Compare direct policy, learned-model planner and privileged oracle-simulator planner.
- [ ] Report prediction accuracy separately from competitive outcome.

**Exit gate:** an agent can enter with a model and common planner; a forecast-only model can enter prediction evaluation without pretending to be a playing agent.

## Phase 9 — Visual and human interfaces

- [ ] Reuse crforge desktop UI for early local play and debugging.
- [ ] Define a deterministic render mode for visual agents.
- [ ] Verify that screenshots show only seat-visible content.
- [ ] Add fixed frame cadence and image dimensions.
- [ ] Implement visual agent runner and separate visual leaderboard.
- [ ] Add a browser-based human-operated interface only after engine/protocol stability.
- [ ] Add human-vs-agent and human-vs-human calibration studies.

## Phase 10 — Release and research paper

- [ ] Publish complete benchmark specification and benchmark card.
- [ ] Publish installation and game-data provenance instructions.
- [ ] Publish code, schemas, baselines and reproducible manifests within licence constraints.
- [ ] Publish fidelity report, unsupported mechanic list and known limitations.
- [ ] Run multiple seeds and sufficient matches for confidence intervals/rating uncertainty.
- [ ] Run ablations on public memory, observation cadence, placement resolution, opponent pool and latency.
- [ ] Verify all claims against logs and artifacts.
- [ ] Complete third-party and game-asset legal review.

## V1 release definition

V1 is not “all AI models play the game”. V1 is:
- one pinned engine and data version;
- one fixed mirrored deck;
- one stable FAIR structured observation;
- one documented action-resolution mode;
- exact public-memory tracking for mechanics covered by tests;
- baseline scripted/random agents;
- an external plugin interface;
- paused-clock competitive tournament;
- match logs and rating uncertainty.

Real-time, visual, human, multi-deck, world-model forecasting and MPC leaderboards can follow as individually versioned tracks. Do not delay the first usable release for every future feature.
