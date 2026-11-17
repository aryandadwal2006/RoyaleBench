# Agent Protocol v1 (Draft)

**Status:** Contract draft. Field-level ObservationV1 is not frozen until the crforge adapter and fair-observation tests exist.

This document defines the interface between RoyaleBench and a lab-provided agent. The benchmark owns the engine, observations, time, actions, tournament and scoring. The lab owns its model and agent logic.

## 1. Supported integration forms

A lab may provide:
- a persistent local subprocess;
- a container image that implements the same stdin/stdout or socket contract;
- a remote HTTP/WebSocket endpoint;
- a hosted LLM/VLM adapter that calls a provider using credentials managed by the participant.

All forms implement the same logical lifecycle. An agent must not receive engine objects, filesystem access to hidden match data, another seat's observation or future state.

## 2. Lifecycle

**Start match:** the runner sends public match configuration and the agent's player seat. It includes the deck because v1 uses mirrored public decks, plus levels, tower setup, observation/action schema versions and declared execution mode.

**Act:** for each decision, the runner sends one observation envelope. The agent returns one action. The runner validates and timestamps it.

**End match:** the runner sends result metadata and permits the agent to flush private diagnostics. Diagnostics do not affect the score.

The agent process may retain private recurrent state between decisions, but that state is reset between matches.

## 3. Structured-state request

A structured request contains:
- protocol/schema version;
- match ID and decision ID;
- engine tick and game time;
- the current player-visible state in the acting player's own frame;
- public event delta since the previous request;
- public-memory block (opponent-elixir count, exactness, possible hand, deduced cycle queue and known card returns);
- action resolution mode and coordinate frame;
- playable hand-slot summary and available ability buttons;
- execution mode and deadline metadata.

The exact field registry will be published after mapping crforge's schema and event stream. Do not hard-code engine vocabulary indices into agent code; names and catalogue digests accompany the match manifest.

### Public memory

The assisted structured track gives every agent the same deterministic memory output. It is derived from initial public information, observed plays, public regeneration rules and visible events. It does not read true opponent hand or post-start opponent elixir from engine state.

Every inferred field has an explicit status:
- exact;
- inferred;
- uncertain;
- unknown.

An unknown queue slot remains unknown. Do not fill it with a guessed card.

### Recent events and compact state

Each request includes a fresh state snapshot plus a bounded event delta. The runner does not send every 50 ms simulator tick to an LLM. The decision cadence is fixed by the match configuration. Agents may store private history, but the initial state is complete enough to start a new process.

## 4. Visual request

A visual request contains:
- one screenshot at the declared decision timestamp;
- optionally a fixed, versioned frame window;
- match metadata which is public under the visual track rules;
- action schema and coordinate semantics.

It does not contain structured entity rows, opponent-cycle tracker, true opponent hand, hidden elixir, internal engine state or privileged event labels. Visual rankings are separate from structured-state rankings.

A later assisted-visual subtrack may add the public-memory block, but it must be separately identified.

## 5. Action response

The action schema is a one-of:
- wait;
- play a hand slot at a point in the acting player's own arena frame;
- press a currently available ability button.

Example play action:

{
  "schema": "royalebench.action.v1",
  "type": "play",
  "hand_slot": 1,
  "x_tile": 8.25,
  "y_tile": 17.50
}

The example illustrates the coordinate convention; the exact allowed coordinate increments are set by the match's action_resolution field. For the existing crforge baseline, only 18 × 32 tile-centre choices exist. Half-tile or fixed-point choices require a tested downstream schema/mask extension and a new action-resolution identifier.

The runner records requested coordinates, quantized point, engine-submitted point, actual landing point, command-given tick, command-run tick, refusal/acceptance and final action status.

The runner must not replace an invalid action with a different card or a strategically better coordinate. Native engine placement search may relocate a tap exactly as the engine's player-command path does; both requested and actual landing points are logged. This is game semantics, not benchmark strategic assistance.

## 6. LLM usage

The intended LLM interface is one decision call per benchmark observation:
- provide the state snapshot, public memory, recent events and action schema;
- use a structured JSON/tool-call output format;
- parse one action;
- validate it;
- return it to the engine.

Do not require three sequential model calls for strategy, card and placement in the primary track. That unnecessarily adds provider latency and makes systems incomparable. A model may reason hierarchically inside one response.

The benchmark does not require a chain-of-thought field. If an agent emits a short explanation, it is diagnostic only and is not scored.

Provider-specific prompt engineering is allowed, but prompts, model identifiers, model versions, sampling settings, tool calls, token usage and latency must be reported.

## 7. World-model interface

A forecasting model is registered separately from a complete playing agent.

Conceptual predictor request:
- FAIR context/history;
- candidate own action sequence;
- horizon and query budget;
- optional opponent-action conditioning mode, explicitly labelled.

Conceptual predictor response:
- predicted future states/events or predicted frames;
- uncertainty/distribution fields where supported;
- model version and inference telemetry.

For dynamics-only evaluation, a teacher-forced joint action sequence can be supplied. This measures conditional transition prediction, not opponent prediction. For opponent-response evaluation, the model predicts the opponent's action distribution using public history. It must not receive the actual future opponent action.

A model-based playing agent combines its predictor with a planner/controller. The benchmark will publish a common planner implementation and candidate-generation budget for the controlled model-based track. Arbitrary custom planners may enter the general agent leaderboard but must declare that fact.

Models producing latent predictions only may enter a model-specific representation study, but cross-model forecasting scores require a common decoded output or a separately defined latent evaluation protocol.

## 8. Timing semantics

### Paused-clock strategic mode
Both agents receive the same decision snapshot and are called concurrently. The engine does not advance until both responses or operational watchdog outcomes are resolved. Latency is measured but does not consume game time. The watchdog and timeout handling are fixed and published.

### Real-time mode
The engine advances on a monotonic wall clock. Late/stale actions are discarded; no action is backdated or applied to a past state. Deadline misses and effective decisions are measured.

An adapter must not infer the timing mode from provider response time. It is explicitly supplied.

## 9. Failure semantics

The runner distinguishes:
- malformed JSON/schema;
- illegal action type/field;
- unaffordable or unavailable card;
- engine refusal;
- agent exception;
- process crash;
- network error;
- watchdog timeout;
- stale real-time action.

Every condition is recorded. No failure silently becomes a successful strategic action. The published rules specify whether the decision becomes wait, a technical match loss or a match void; engine faults are never counted as agent losses.

## 10. Reproducibility metadata

Every agent submission declares:
- agent name and version;
- source/container digest;
- model provider, exact model ID and version where available;
- prompt/config hash;
- observation modality and schema version;
- training engine/data version;
- training data provenance and whether privileged training observations were used;
- action-resolution mode;
- required CPU/GPU/memory;
- expected provider/API dependencies;
- licence and release restrictions.

Proprietary model weights need not be published, but model identity and the limits on reproducibility must be disclosed.

## 11. Security boundary

Untrusted lab code must run outside the engine process. Containers should have:
- no host filesystem mounts except explicit read-only protocol inputs;
- no access to engine memory or hidden replay paths;
- no access to the other agent's process or credentials;
- outbound network disabled by default for local code submissions;
- resource limits and process timeouts.

Hosted API credentials are provided by the participant through the runner's secret mechanism and are not committed to the repository or stored in match logs.
