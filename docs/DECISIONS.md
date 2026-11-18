# Architecture Decision Records (Initial)

These are current design decisions for RoyaleBench v1. They can change only through a dated amendment that records the evidence and migration impact.

## ADR-0001: Use crforge as the canonical v1 battle engine candidate

**Status:** Accepted provisionally, subject to Phase 1 acceptance tests.

**Decision:** Use crforge as the single official battle engine for v1. Keep its source as a pinned Git submodule and integrate through its environment/Python wrapper. Do not copy the battle core into RoyaleBench.

**Reasons:** 50 ms deterministic ticks, native player-command semantics and delay, tick-level reference conformance, replay support, two-seat environment and existing interactive desktop visualizer.

**Consequences:** RoyaleBench must pin crforge's exact commit and game-data version/hash. Unsupported or unvalidated mechanics are excluded from the initial deck and benchmark claims. A future RoyaleSim leaderboard is a distinct engine track, not an interchangeable runtime.

**Revisit when:** crforge cannot be built/reproduced from public instructions, a required mechanic is unsupported, data access is not viable, or a different engine demonstrates stronger reproducible fidelity for the chosen scope.

## ADR-0002: Fixed mirrored decks for v1

**Status:** Accepted.

**Decision:** Both participants use the same public eight-card deck, equal levels, equal tower configuration and equal slot/evolution setup. Initial hand and hidden cycle order remain private.

**Reasons:** The first benchmark should isolate in-match decision quality, opponent inference, placement and timing. Deck-building would add a separate optimization task and confound match outcomes.

**Consequences:** V1 does not rank deck selection. Multiple deck archetypes can be added later as separate balanced strata.

## ADR-0003: Provide a common deterministic public-memory block

**Status:** Accepted; implemented in ObservationV1 using CRForge's seat-side elixir accounting and a public-play card-cycle tracker.

**Decision:** In the assisted structured track, RoyaleBench computes opponent-elixir accounting and card-cycle deductions from public observations/events and supplies the same memory state to every agent.

**Reasons:** Opponent elixir arithmetic and card-cycle bookkeeping are important game mechanics, but the primary v1 leaderboard should focus on strategic decisions rather than whether an LLM can manually count a long event transcript.

**Consequences:** A separate raw-history track can later test memory/inference itself. Every memory field must expose exact/inferred/uncertain/unknown status. No hidden engine values may enter the public tracker.

## ADR-0004: Direct per-decision LLM interface, not code generation, for the primary LLM track

**Status:** Accepted.

**Decision:** The primary LLM track receives one standardized observation per decision and returns one structured action: wait, play a hand slot at a location, or ability button. The model may reason hierarchically internally, but it does not need three sequential strategy/card/placement API calls.

**Reasons:** This measures playing decisions and avoids conflating them with code synthesis or adding avoidable serial inference latency.

**Consequences:** Code-writing agents may enter a separate program-synthesis track later. LLM explanations are not scored.

## ADR-0005: Separate paused-clock strategic strength from real-time performance

**Status:** Accepted.

**Decision:** Maintain two independent evaluation modes:
- paused-clock lockstep: both agents observe the same simulated tick; inference calls run concurrently; game advances only after both responses or watchdog outcomes;
- real-time: game advances at the declared wall-clock rate; late/stale actions are discarded and counted.

**Reasons:** A single leaderboard cannot fairly combine strategic decision quality with variable provider/network/model speed.

**Consequences:** Every submission reports latency. Rankings are separate. The paused-clock mode uses a proposed 120-second per-response operational watchdog. A watchdog timeout is a technical void/failure rather than an agent loss; completion and timeout rates are reported. Real-time mode uses one outstanding request per agent and a 250 ms observation opportunity at 1× game speed.

## ADR-0006: Target half-tile placement lattice, with tile-centre baseline fallback

**Status:** Superseded for v1 by ADR-0010; retained as a possible future extension.

**Decision:** The desired v1 action resolution is a 36 × 64 half-tile lattice. The agent expresses a cell centre as x_tile/y_tile in board-tile units (0.25, 0.75, 1.25, ... horizontally; 0.25, 0.75, ... vertically); the adapter maps those values to integer routing-cell coordinates and uses the engine's native placement search. The current crforge Python action schema is 18 × 32 tile-centre; it does not already expose the half-tile grid.

**Reasons:** Placement location is strategically important. Half-tile action granularity is a practical common interface for LLMs, RL policies and world-model planners and has a precedent in RoyaleGym's action design. It avoids an enormous continuous-action search while offering finer control than tile-centre actions.

**Execution semantics:** Use crforge's MASK_ALL_TILES semantics so the action represents a tap point; native placement search chooses the actual landing point. Log requested point and actual landing. Do not pre-filter positions using MASK_LANDING_TILES in the primary tap-point track.

**Consequences:** Implement and test the action-schema/mask patch against the pinned crforge commit. If 36 × 64 cannot be made correct, release a separately named tile-centre action mode rather than silently changing resolution. Future finer point-action modes get their own action schema/leaderboard.

## ADR-0007: Pin upstream repos as submodules; copy only small tested utilities

**Status:** Accepted.

**Decision:** Keep crforge, RoyaleGym and RoyaleSim at exact commits under third_party/upstream. Do not vendor entire repos into the RoyaleBench Python package. Copy/adapt only minimal, identified public-memory helpers from RoyaleGym after source audit and differential testing.

**Reasons:** This preserves attribution, makes upstream diffs visible, avoids maintaining duplicate engines and keeps RoyaleBench's code focused on benchmark infrastructure.

**Consequences:** Any copied source must retain its licence notice and provenance comments. Supercell game tables/assets are excluded unless separately licensed.

## ADR-0008: Keep observation modalities and model classes in separate leaderboards

**Status:** Accepted.

**Decision:** Separate structured FAIR agents, visual agents, world-model forecasts, model-based playing agents, and real-time agents. No single rating merges different observation information or execution modes.

**Reasons:** A structured state input and a screenshot are different tasks; a forecasting model and a complete controller are different artifacts; paused-clock and real-time matches measure different capabilities.

**Consequences:** Publish cross-play matrices and shared baselines where meaningful, but only compare within declared compatible tracks.


## ADR-0009: Use Glicko-2 for 1v1 competitive ratings

**Status:** Accepted.

**Decision:** Use Glicko-2 for the primary 1v1 rating. Initial parameters: rating 1500, rating deviation 350, volatility 0.06, tau 0.5. Update at the end of complete published rating periods, using the full batch of match results against pre-period opponent ratings.

**Reasons:** RoyaleBench v1 is a two-player competitive benchmark. Glicko-2 explicitly tracks uncertainty and rating volatility; raw win percentage alone is unstable when submissions have different match counts.

**Consequences:** Every leaderboard exposes rating deviation, match count, W/D/L and confidence intervals. A paired side-swap contributes both games to the rating-period result set. Publish the rating-period definition and exact implementation/version. Ratings remain separate by observation modality, latency mode, action-resolution version and deck stratum.

## ADR-0010: Freeze tile-centre actions for RoyaleBench v1

**Status:** Accepted for v1.

**Decision:** RoyaleBench v1 uses the pinned CRForge 18 x 32 tile-centre action grid and `MASK_ALL_TILES=1`. An agent supplies a tap point at a tile centre; CRForge's native PlayerCommands placement search and 20-tick command delay remain authoritative. The adapter does not silently snap invalid coordinates or replace invalid actions.

**Reasons:** This is the action contract exposed by the pinned CRForge environment and can be tested without modifying upstream action semantics. A higher-resolution action grid would require a separate, versioned adapter and differential placement tests.

**Consequences:** The 36 x 64 half-tile proposal in ADR-0006 is not part of the v1 leaderboard. A future half-tile track must receive a distinct action-resolution identifier and its own compatibility tests. Never compare its ratings directly with tile-centre ratings.

**Revisit when:** A pinned engine extension exposes a verified higher-resolution tap lattice while preserving native placement semantics and reproducible replay behaviour.
