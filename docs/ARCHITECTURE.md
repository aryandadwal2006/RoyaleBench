# RoyaleBench Architecture and Design Specification

**Status:** Architecture and implementation record. The v1 implementation status and remaining acceptance gates are tracked in [ROADMAP.md](ROADMAP.md).  
**Repository:** aryandadwal2006/RoyaleBench  
**Decision baseline:** 2026-11-18  
**Scope:** Offline, reproducible 1v1 Clash Royale-style competition for agents supplied by research groups.

---

## 1. Product definition

RoyaleBench is an evaluation harness, not a new game engine and not a bot that logs into official Clash Royale accounts.

RoyaleBench supplies:
- a version-pinned battle engine and reproducible match configuration;
- the observation protocol and public-information bookkeeping;
- the action protocol, placement semantics and command scheduling;
- agent adapters and a local/remote execution boundary;
- tournament scheduling, paired side swaps, replays and ratings;
- separate strategic-strength and real-time evaluations;
- separate prediction evaluation for learned world models;
- an optional human-operated interface over the offline simulation.

A lab supplies an agent that implements the protocol. That agent can be an LLM, VLM, RL policy, scripted controller, world model plus planner, or hybrid.

The benchmark must not conflate three different objects:
1. **Predictive model:** predicts future states from observations and actions.
2. **Policy/controller:** selects actions from observations.
3. **Model-based agent:** uses a predictive model and a controller/planner to select actions.

A world model without an action-conditioned prediction interface can enter a forecasting track, but cannot be described as a model-based playing agent merely by wrapping it in a policy.

## 2. Design principles

1. **One official game implementation per leaderboard release.** Engine and game-data versions are part of every result identity.
2. **One information contract per track.** Agents in a track receive the same player-visible information and no hidden simulator state.
3. **One action contract per track.** Card choice, placement coordinates, command delay and rejection semantics are standardized.
4. **The simulator is authoritative.** The agent proposes an action; the environment executes it through the engine's player-command path.
5. **No strategic action repair.** The benchmark must not quietly replace an invalid or poor action with a better one.
6. **Separate strength from speed.** A paused-clock strategic leaderboard and a wall-clock real-time leaderboard answer different questions.
7. **Match outcomes are the competitive score.** Prediction accuracy, elixir efficiency, crown differential and other measurements are diagnostics or separate research metrics.
8. **Do not combine incomparable tracks into one ranking.** Structured-state agents, visual agents, world-model forecasts and real-time agents get separate leaderboards.
9. **Reproducibility is mandatory.** Seeds, engine commit, data version/hash, schema versions, decks, levels, agent hashes and execution settings accompany every match.
10. **Do not distribute game assets without rights.** Upstream source licences do not license Supercell's game tables, images, sounds or trademarks.

## 3. Engine decision

### 3.1 Canonical engine: crforge

Use [voonhous/crforge](https://github.com/voonhous/crforge) as the proposed canonical engine, subject to the acceptance tests in the roadmap.

Why:
- Its battle core runs at 50 ms integer ticks.
- It routes plays through the game's PlayerCommands path.
- It models the command delay rather than spawning a card immediately.
- Its conformance suite compares simulator traces with recorded game traces tick by tick, with no tolerance.
- It exposes a two-seat environment, masks, per-seat observations, replays, replay labelling and a Python PettingZoo wrapper.
- It already has an interactive desktop visualizer that permits manual play from either side, pause/step, unit inspection and replay inspection.
- Its current documented reference target is client 16.635.1, with 16.635.3 and 16.635.8 data versions. The 16.635.10 client was noted but not established as the engine's reference target in the inspected compatibility page.

Important limitation: crforge is not proved correct for every card, ability, evolution, champion or future game release. A benchmark release must publish the fidelity report, unsupported-mechanic list and exact data hash. A simulator fault or unsupported mechanic is not a win/loss.

### 3.2 Why RoyaleGym/RoyaleSim is not the v1 official engine

[RoyaleGym](https://github.com/RoyaleGym/RoyaleGym) and [RoyaleSim](https://github.com/RoyaleGym/RoyaleSim) are exceptionally useful references:
- Python-native Gymnasium/PettingZoo workflow;
- structured spatial and entity-list observations;
- fair/reveal separation;
- opponent elixir accounting;
- card-cycle and enemy-queue inference;
- action-mask and half-tile action design;
- renderer/viewer and existing training ecosystem.

However, RoyaleSim's own accuracy page describes a bounded evaluation: 73 recordings from 40 matches, 76 basic cards and one hero; it states that champions and evolutions were not covered by that measurement. This is useful evidence, not universal fidelity proof. Its 16.635 table and data provenance also need separate scrutiny.

Therefore:
- crforge is the v1 runtime candidate;
- RoyaleGym/RoyaleSim are pinned reference implementations and possible independent validation tools;
- do not silently mix engine state, replays, action semantics or results across the two engines;
- a future second-engine leaderboard would be explicitly separate and versioned.

### 3.3 Engine acceptance gate

Before calling crforge the official engine:
- run the Java build and all tests on a clean machine;
- build one supported data version and record the exact data hash;
- run its conformance tests and save the report;
- verify all cards and mechanics included in the v1 deck;
- verify both sides' observations and masks;
- test command delay, placement search, reserved elixir and ability commands;
- test deterministic replay from seed plus actions;
- test terminal results and faults;
- check that a public user can obtain the required tables lawfully and repeat the setup.

Do not use a card in the initial fixed deck if the corresponding behaviour is unsupported or has not passed the required tests.

## 4. Match format: remove avoidable confounders

### 4.1 V1 uses fixed mirrored decks

Deck construction is not part of the first benchmark. Both competitors receive the same eight-card deck, levels, tower configuration, tower troop and evolution/hero slot setup.

The starting hand, shuffle and hidden cycle order are independently seeded and hidden. A participant knows the deck list because the benchmark rules make it public, but does not receive the opponent's actual hand, next card or true elixir.

A match configuration pins:
- deck card names and order;
- levels and tower setup;
- slot flags for evolutions/heroes;
- engine and game-data version;
- starting conditions;
- observation interval;
- command delay;
- action resolution mode;
- seed derivation;
- overtime and terminal rules.

V1 should prove one deck and one clean action/observation protocol before expanding to a small fixed deck suite. Later releases can include multiple archetypes as separate matchup strata. Deck selection and deck-building remain a separate future task.

### 4.2 Paired side swaps

For each matchup, run paired games with:
- the same engine version and configuration;
- the same deck and levels;
- seat assignments reversed;
- independently derived, recorded hidden seeds.

Where possible, use common-random-number evaluation for paired policy comparisons. Do not assume one seed produces identical stochastic events after the policies take different actions; the seed protocol must be documented and the resulting trajectories logged.

## 5. Observation architecture

There are two official observation modalities and they must have separate rankings.

### 5.1 Structured FAIR track

The agent receives a versioned structured snapshot in its own board frame (its king tower is at the bottom). The canonical observation has these blocks:

**Match clock**
- engine tick and game time;
- phase: regulation, overtime or tiebreaker;
- elixir regeneration rate;
- decision ID and observation timestamp.

**Own state**
- current elixir and reserved/pending elixir;
- four hand slots with card identity, cost and playability state;
- next card and known own cycle;
- own towers, crowns and ability-button state.

**Board**
- visible entities with stable seat-local IDs;
- owner, card/source identity where visible, unit type, position, HP only where visible, max HP where legitimately known, movement/status, target information where visible;
- projectiles and visible spell/effect objects;
- tower health and state;
- entity overflow/truncation flags.

**Opponent public-memory state**
- public cards observed as played;
- full deck list only because v1 uses mirrored, public decks;
- possible opponent hand, not actual hand;
- inferred next/queue positions only where deduced;
- opponent-elixir count with exactness/uncertainty indicator;
- estimated remaining plays until each card returns;
- public ability/evolution observations and cycle progress when inferable.

**Recent event ledger**
- only events that are visible to the acting player;
- play observed, unit appeared, spell launched/landed, damage/health-bar update, death, tower damage, ability/evolution indication;
- event tick or tick interval and confidence/visibility source.

**Action protocol descriptor**
- action schema version;
- coordinate frame and resolution mode;
- which hand slots can currently be attempted;
- ability-button availability;
- command delay and any pending commands;
- no hidden action candidates or future states.

The canonical state is a snapshot plus a bounded event delta. Agent SDKs may maintain private recurrent memory, but may not access engine objects or other players' observations.

### 5.2 Visual track

The visual agent receives:
- a rendered screenshot at the benchmark decision interval;
- optionally a fixed number of recent frames at fixed timestamps;
- no structured entity list, hidden state, opponent-hand data or engine oracle fields.

The visual rendering must be deterministic and versioned. It should use original benchmark artwork or an upstream renderer only where the relevant licence permits it. Do not redistribute Supercell images or sounds without permission.

The action API is identical to the structured track. Visual and structured results are not merged into one rating because one task includes perception and the other does not.

### 5.3 FAIR means no hidden-state leakage

The observation builder must never read:
- actual opponent hand;
- actual opponent next card or queue;
- actual opponent elixir after initial public information;
- opponent commands not yet visible;
- future simulator state;
- unrevealed spell aim points;
- internal RNG state or hidden seed;
- hidden entity HP or identity where the player's visibility rules do not expose them.

V1's mirror-deck rule makes the deck list public, not the opponent's initial cycle.

Every observation field must be tagged as one of:
- directly visible;
- deterministically inferred from public events/rules;
- estimated/probabilistic;
- unknown;
- privileged oracle (not available to official agents).

The public-memory implementation must publish its version and exactness flags.

## 6. Opponent elixir and card-cycle memory

This is a benchmark service, not a test of whether each LLM can perform arithmetic over a long transcript. V1 supplies every agent in the assisted track with the same deterministic public-memory state.

### 6.1 Opponent elixir

Start from the publicly visible initial amount. Advance the known regeneration schedule using integer engine ticks, clamp at the cap, subtract the cost of every publicly observed opponent play and account for publicly observable income, refunds and special card effects when their mechanics are supported.

Never read the actual opponent elixir from the engine after match start.

The tracker emits:
- estimated amount;
- exactness flag;
- known missing/unmodelled income/effect causes;
- public plays used to update the counter.

If the accounting can no longer be guaranteed exact, mark it inexact. Do not fabricate certainty.

### 6.2 Opponent cycle

For an eight-card distinct deck, a played card goes to the back of the cycle. Maintain:
- set of cards observed played;
- possible current four-card hand;
- ordered deduced queue behind the hand, when enough observations exist;
- per-card number of opponent plays until it can return;
- unknown slots where the order cannot yet be inferred.

Do not infer an exact current hand merely from a set of cards seen. Refills, pending plays and observation gaps matter. The implementation must be tested against engine state as an oracle during development, but the oracle is never passed to the agent.

### 6.3 Source to adapt

RoyaleGym's observation implementation and tests are the reference for:
- MatchMemory and MatchClock;
- fair_fields;
- enemy_possible_hand;
- enemy_queue_5_8;
- enemy_card_cycle;
- elixir_income and its exactness/failure cases;
- tests for enemy queue, fair fields, elixir income and ability presses.

Do not copy the entire RoyaleGym observation builder into the crforge adapter. Extract the smallest engine-independent memory logic, then write a crforge event adapter and differential tests. Keep the MIT notices for any source copied or adapted.

## 7. Action protocol and exact placement

### 7.1 Single conceptual action format

All agents submit one of:
- wait;
- play one of the four hand slots at an arena point;
- press an available ability button.

The canonical conceptual JSON action is:

{
  "schema": "royalebench.action.v1",
  "type": "play",
  "hand_slot": 1,
  "x_tile": 8.25,
  "y_tile": 17.75
}

Coordinates are in the acting player's own frame, with x increasing right and y increasing from own back line toward the opponent. A wait action has only type=wait. Ability actions identify the publicly available button index.

The adapter converts the coordinates into the engine's integer world units. It logs:
- requested point;
- snapped/quantized input point;
- point submitted to the player's command path;
- actual landing point returned by native placement;
- refusal/placement reason;
- command-given tick and command-run tick.

### 7.2 Placement resolution modes

Do not claim higher precision than the engine supports. The inspected crforge Python schema currently exposes 18 × 32 tile-centre placement choices for each hand slot (plus wait and ability actions). Its underlying player-command path performs placement search, but the Python action schema is not currently a continuous or half-tile public action interface.

**V1 target: Mode B, half-tile action grid.** Extend the crforge environment schema and masks to a 36 × 64 routing-cell-centre grid. The agent emits x_tile/y_tile at the centre of one half-tile cell (0.25, 0.75, 1.25, ..., 17.75 horizontally; 0.25, 0.75, ..., 31.75 vertically). This is a downstream schema/mask patch, not an existing crforge feature. RoyaleGym's 36 × 64 design is a reference, not proof that the same patch is correct for crforge.

The current crforge 18 × 32 tile-centre codec remains the fallback for local acceptance tests. If the half-tile patch fails, a tile-centre leaderboard must carry a distinct action-resolution ID; do not pool its ratings with half-tile agents.

Fixed-point continuous coordinates are a possible later action schema, not a v1 requirement.

For touch-point semantics, configure the crforge environment to use its MASK_ALL_TILES rule (once verified against the pinned engine): a playable hand slot exposes every action-grid point as a tap point, and the engine's own placement search determines the actual landing tile. Do not use MASK_LANDING_TILES as a strategic filter for the official tap-point agent track, because that would pre-filter placements the client would ordinarily accept and relocate. The mask should gate whether the card can be attempted; native placement search should own the location resolution. This choice must be confirmed by placement regression tests and recorded in the match manifest. The initial code should implement Mode A as a working baseline and test Mode B/C before selecting a higher-precision v1 release. The target is Mode B or C, not a claim that they already exist.

### 7.3 Do not provide a giant LLM action list

A 9,000-item placement list is not a workable LLM interface. The agent receives the current hand, costs, board, the fixed action format and the native placement semantics. It outputs card slot and coordinates directly.

The engine performs the same placement search for every agent. It does not choose a strategically better coordinate on the agent's behalf. A card that cannot be played is refused according to the engine's command semantics; the rejection is logged. A coordinate that the game client would relocate is relocated by the same native placement search, with requested and actual positions both recorded.

Do not give one agent a strategically curated shortlist of placements while another must search the full arena.

## 8. Agent plugin interface

The benchmark owns the game and scheduler. Labs provide only an agent implementation.

### 8.1 Lifecycle

Required operations:
- initialize once with agent metadata and protocol versions;
- reset per match with public match configuration, player seat and own-deck metadata;
- act on each observation;
- close and flush optional diagnostic output.

A stateless HTTP adapter and a persistent local process adapter must both be supported. Agent memory must be private to that agent and match. No agent may read opponent process memory, simulator files or hidden state.

### 8.2 Agent input

Every invocation receives:
- protocol/schema version;
- match/decision ID and game tick;
- exactly one modality (structured FAIR snapshot or visual frame packet);
- public-memory block if using the assisted structured track;
- action schema and coordinate resolution;
- decision/deadline metadata appropriate to the leaderboard.

### 8.3 Agent output

One structured action and optional diagnostics:
- action;
- optional agent-side confidence or rationale fields, never used for scoring;
- optional opaque model-specific telemetry.

The benchmark validates parsing, ranges, hand slot, action kind and protocol version. It does not silently change an action into a different card or placement.

### 8.4 Lab integration modes

Support three deployment forms:
1. **Local subprocess/container:** lab supplies a container or command implementing the SDK.
2. **Remote HTTP/WebSocket endpoint:** lab hosts the agent; benchmark sends observations and receives actions.
3. **Hosted-model adapter:** a participant supplies a provider/model identifier and credentials through their own adapter. The benchmark should not store provider API keys.

A lab should not need to fork the simulator, renderer, scheduler or rating implementation.

## 9. Agent classes and leaderboards

### 9.1 Competitive agent leaderboard

Any complete controller can enter:
- LLM structured agent;
- VLM visual agent;
- RL policy;
- imitation-learning policy;
- scripted policy;
- recurrent policy;
- world-model-plus-planner agent;
- hybrid agent.

Separate rankings by observation modality and execution mode. Later add deck strata.

### 9.2 LLM/VLM track

Primary v1 LLM task: one direct decision per benchmark observation. The model is not asked to write arbitrary executable code.

Prompt/adapter provides:
- current observation;
- public opponent memory;
- recent events;
- available hand and resource state;
- the action schema and placement-coordinate semantics.

It returns wait, play(hand_slot,x,y) or ability(button). JSON/tool-call output is validated by the adapter. The model may reason internally, but the benchmark does not score prose.

Code-generation agents can be added as a separate track later. They measure program synthesis, agent engineering and strategy together, not the same capability as live per-decision play.

### 9.3 World-model tracks

**Forecast track:** model receives only FAIR context/history and an action sequence that is known up to the prediction point. It predicts future state/events at declared horizons. Teacher-forced opponent actions may be supplied for dynamics-only diagnosis, but this is explicitly not adversarial response prediction.

**Opponent-response track:** model predicts distributions over opponent actions from the public history. It never receives actual future actions.

**Model-based playing track:** model is connected to a common planner/controller. The planner generates candidate action sequences, queries the world model, scores predicted futures and executes only the first action. Report the model and planner separately.

For a fair comparison, publish planner version, candidate-generation rules, opponent hypotheses, rollout horizon, number of model queries, search budget and compute. A black-box video generator that cannot condition on the candidate actions may enter visual forecasting, but cannot enter the action-conditioned planner track.

### 9.4 RL and policy track

RL and imitation agents use the same structured FAIR interface and action schema. The benchmark does not require all participants to use the same network architecture or training data. It does require disclosure of training information, environment version and any privileged training-only data. Evaluation observations remain fair.

### 9.5 Human track

Humans play through a benchmark-owned, human-operated interface over the offline simulator. This is optional and separate from the automated-agent leaderboard. No official Supercell account automation, account sharing or live-game control is part of RoyaleBench.

## 10. Latency and execution modes

Different models have fundamentally different inference costs. A single ranking that ignores latency is misleading; a single ranking that always penalizes latency also confounds strategic quality with hardware/provider speed.

### 10.1 Strategic-strength mode: paused-clock lockstep

This is the primary outcome leaderboard.

At each decision:
1. The engine advances to the fixed decision tick (five 50 ms ticks by default).
2. It freezes the game state.
3. Both seats receive observations from that same simulated tick.
4. Both agent calls are launched concurrently.
5. The engine waits for both responses or the operational watchdog.
6. Actions are timestamped against the frozen decision and passed through the native player-command path.
7. The engine advances by the configured number of game ticks.

Proposed v1 operational watchdog: 120 seconds per response. A watchdog timeout is a technical failure/void, not silently converted into an agent loss. Publish timeout rate and match-completion rate.

Consequences:
- A slow LLM does not lose simulated game time while thinking.
- A fast RL agent cannot play several times while its opponent is thinking.
- Both agents get the same number of decision opportunities.
- Response latency is still measured and reported.
- The strategic rating measures decision quality under a generous operational watchdog, not real-time responsiveness.

### 10.2 Real-time mode: wall-clock 1× simulation

The engine advances at 1× game speed: one 50 ms game tick per 50 ms wall-clock time. An observation opportunity occurs every 250 ms, but only when that agent has no outstanding request. Each agent has at most one in-flight request.

The engine never waits for inference. When a response arrives:
- it is applied at the current engine tick, never backdated;
- the response must match its request/decision ID;
- for a play, the expected_card must still occupy the specified hand slot;
- native placement search and the 20-tick command delay begin at the actual arrival tick;
- otherwise the action is rejected as stale or invalid.

While a request is outstanding, that agent receives no new observation and cannot issue another action. A slow LLM therefore reacts less frequently while the game continues. This deliberately measures the interaction of strategy, latency and reliability.

A 120-second watchdog invalidates a hung request. A timeout/missed decision is logged and handled using the published no-action rule. Report achieved action frequency, stale/rejected actions and end-to-end latency.

### 10.3 Report latency, do not hide it

For every submission report:
- P50, P95, P99 and mean end-to-end decision latency;
- timeout and deadline-miss rates;
- effective decisions per simulated minute;
- total wall-clock match time;
- token/input/output usage for LLM APIs where available;
- provider/model identifier and version;
- API cost if the participant supplies it;
- CPU/GPU time and peak memory where measurable;
- world-model encoding, prediction, planning and decoding time separately.

For a world-model planner:

T_agent = T_encode + T_predict + T_plan/search + T_decode + T_transport.

For LLMs, include network/provider latency and all tool/model round trips. Do not use vendor-reported token-generation latency as the benchmark latency.

### 10.4 Context and repeated observations

Do not stream every 50 ms engine tick to an LLM. The benchmark decision cadence is fixed. An LLM receives a compact current snapshot, public-memory summary and a bounded recent-event delta. Persistent agents may maintain their own hidden memory. VLMs receive the same number and timing of frames. Track-specific input limits and image sizes are published.

## 11. Tournament scheduling and rankings

### 11.1 Match schedule

Each submission plays:
- a fixed baseline set (random, scripted aggressive, scripted defensive, frozen reference policy);
- a balanced sample of other submissions;
- both sides through paired matches;
- a fixed deck/configuration and hidden seed schedule.

Use an evaluation seed set not used for training. Hidden evaluation seeds are generated and stored by the benchmark service. Agent containers cannot read them.

### 11.2 Rating

Use Glicko-2 for the 1v1 competitive rating. Initial values: rating 1500, rating deviation 350, volatility 0.06, system constant tau 0.5. Update only at the end of a complete published tournament rating period, using all game results in that period against the opponents' pre-period ratings. A paired side-swap contributes both game results; do not collapse a 1-1 split into an arbitrary win/loss. Pin the implementation/version, period definition and update order. Publish rating deviation alongside the rating. Do not rank by raw win percentage alone.

Report alongside the rating:
- W/D/L and win-rate confidence intervals;
- match count and rating uncertainty;
- crown differential;
- results by side and opponent;
- results by fixed deck/matchup stratum;
- timeout/invalid-action counts.

No single global rating should merge structured and visual tracks, paused-clock and real-time modes, or incompatible action-resolution schemas.

### 11.3 Match outcomes are primary

Win/draw/loss is the main competitive outcome. Crown differential and tower HP are diagnostics/tiebreak analyses, not a large hand-designed weighted score that overrides wins.

Prediction metrics do not contribute to competitive agent rating.

## 12. World-model evaluation

The forecast benchmark uses held-out trajectories grouped by match/replay/seed, not random individual frames. It evaluates multiple horizons, for example 0.5, 1, 2, 5 and 10 game-seconds, with the actual supported horizon set pinned per release.

Metrics should include:
- unit/entity presence and identity precision/recall;
- position error in tiles;
- HP/tower-health error where visible/labelled;
- spawn/death/event precision/recall/F1;
- projectile/effect position and timing;
- resource trajectory error;
- card-cycle and public-memory prediction accuracy;
- probabilistic calibration/log score where distributions are produced;
- multi-step rollout drift;
- counterfactual ranking accuracy: whether the model ranks alternative actions in the same order as controlled simulator outcomes.

For counterfactual evaluation, fork the same saved starting state, vary one action or action sequence, and compare the model's predicted differences with true engine rollouts. Record opponent-policy assumptions. Do not claim that one passive next-state metric proves strategic utility.

A separate experiment connects model prediction to decision quality:
- direct policy baseline;
- the same policy with a learned-model planner;
- a fixed planner using the oracle simulator for an explicitly privileged upper-bound reference.

Use the same action candidates, starting states, opponent population and compute/rollout budget where meaningful. Report both match outcome and prediction/planning metrics.

## 13. Reproducibility and trust boundary

Every match manifest records:
- RoyaleBench version and Git commit;
- engine submodule commit and engine schema version;
- game-data version, content hash and provenance;
- action schema and placement resolution;
- observation schema and memory-tracker version;
- deck, levels, tower setup, seed identifier and side assignment;
- agent source/container hash, declared model ID/version and config;
- observation cadence, command delay, latency mode and timeouts;
- start/end tick, replay reference and final result;
- per-decision requested action, accepted/rejected status, requested/actual placement, timestamps and latency.

The agent process must not receive:
- simulator process memory or raw Battle object;
- filesystem paths to hidden engine/replay state;
- hidden seed or other seat's observation;
- future states or ground-truth opponent actions in competitive play.

The environment must separate training, validation and hidden evaluation data. Public baseline matches cannot reveal the hidden test seed set.

## 14. Intended source tree

The v1 runtime is pinned to CRForge commit `fa5959055c590a493d62c8dbc804e602832d08a6` and game-data version `16.635.8` with content SHA `062a11e0500c03cc041f123413b1ef1846b539a4`; startup rejects a different source checkout or data fingerprint. The detailed tree is recorded in the repository README and ROADMAP. Conceptually:

- third_party/upstream: pinned source references only;
- src/royalebench/engine: crforge adapter and engine capability checks;
- src/royalebench/observations: FAIR schema, event ledger, public memory, visual frames;
- src/royalebench/actions: action types, coordinate transforms, placement validation and resolution modes;
- src/royalebench/agents: SDK, subprocess runner, container runner, HTTP runner;
- src/royalebench/llm: optional provider-neutral structured-output adapters;
- src/royalebench/world_models: prediction protocol and model registration, not mandatory model architectures;
- src/royalebench/planning: shared candidate generation and MPC interfaces;
- src/royalebench/tournament: schedules, pairing, seed derivation, ratings;
- src/royalebench/latency: lockstep and real-time clocks, deadlines and telemetry;
- src/royalebench/evaluation: match, forecast, counterfactual and statistical evaluation;
- schemas: JSON Schema for observations, actions, agents and result manifests;
- configs: engine, decks, action resolutions and evaluation suites;
- tests: determinism, fairness/no-leak, cycle/elixir, placement, replay and tournament tests;
- docs: protocol, API, contribution, benchmark cards and paper protocol.

## 15. Non-goals for v1

- Building a new Clash Royale engine from scratch.
- Deploying bots on official Clash Royale accounts or controlling live accounts.
- Deck-building optimization.
- A single cross-modal universal rating.
- Scoring LLMs by the quality of their written explanation.
- Treating generated plausible video as proof of action-conditioned world modelling.
- Bundling Supercell game tables/artwork or private replays without permission.
- Copying entire unrelated agent projects into the runtime.
- Claiming exact placement or complete game fidelity before the corresponding tests pass.

## 16. Open decisions that require evidence, not preference

The following remain explicit gates:
1. Does the selected crforge data version support every chosen fixed-deck mechanic?
2. Which engine event stream is sufficient to port RoyaleGym's opponent-elixir and cycle logic exactly?
3. Can the crforge environment expose half-tile or fixed-point placement without changing native placement semantics?
4. What observation cadence preserves enough value for exact timing decisions while remaining feasible for hosted LLMs?
5. What per-decision watchdog is operationally reasonable for the paused-clock leaderboard?
6. Does the benchmark renderer show only player-visible information, including invisible/tunnelling units and unrevealed spell aim?
7. Which game-data and replay inputs can be legally obtained, used and redistributed?

No answer should be hard-coded until tested and recorded in an ADR (architecture decision record).

---

## 17. Primary upstream references

- crforge source and docs: https://github.com/voonhous/crforge
- crforge environment: https://github.com/voonhous/crforge/blob/main/docs/environment.md
- crforge schema: https://github.com/voonhous/crforge/blob/main/env/src/main/java/org/crforge/env/Schema.java
- crforge desktop: https://github.com/voonhous/crforge/blob/main/docs/architecture.md
- RoyaleGym source: https://github.com/RoyaleGym/RoyaleGym
- RoyaleGym observation contract: https://github.com/RoyaleGym/RoyaleGym/blob/main/docs/observation-spec.md
- RoyaleGym observation implementation: https://github.com/RoyaleGym/RoyaleGym/blob/main/royalegym/obs.py
- RoyaleSim API: https://github.com/RoyaleGym/RoyaleSim
- RoyaleViser: https://github.com/RoyaleGym/RoyaleViser

The corresponding exact commits are pinned in third_party/upstream and in the third-party register.
