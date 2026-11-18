# Agent Protocol v1 (Draft)

**Status:** Implemented v1 contract, pending final local CRForge acceptance. Machine-readable schemas live in `schemas/`; the JSONL subprocess transport is implemented by `SubprocessAgent`.

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

The agent process may retain private recurrent state between decisions. RoyaleBench starts a fresh subprocess per match, so recurrent state is reset at the match boundary.

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

The field registry is represented by `schemas/observation.v1.schema.json` and the converter in `src/royalebench/observations.py`. Card, entity and buff identifiers are exposed as names where possible; engine vocabulary indices remain an implementation detail. Engine/data version and vocabulary hashes are recorded in the observation and match manifest.

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

Every act request carries a unique request_id, monotonically increasing decision_id and SHA-256 observation_hash. The agent must echo all three in the response envelope:

{
  "schema": "royalebench.agent-response.v1",
  "request_id": "opaque-request-id",
  "decision_id": 328,
  "observation_hash": "64-character-lowercase-sha256",
  "action": {
    "schema": "royalebench.action.v1",
    "type": "wait"
  }
}

The runner accepts a response only for the outstanding request and matching observation hash. The envelope is defined by schemas/agent-response.v1.schema.json; the nested action is defined by schemas/action.v1.schema.json.

The action schema is a one-of:
- wait;
- play a hand slot at a point in the acting player's own arena frame;
- press a currently available ability button.

Example play action:

{
  "schema": "royalebench.action.v1",
  "type": "play",
  "hand_slot": 1,
  "expected_card": "Cannon",
  "x_tile": 8.5,
  "y_tile": 17.5
}

The example illustrates the coordinate convention; the exact allowed coordinate increments are set by the match's action_resolution field. For the existing crforge baseline, only 18 × 32 tile-centre choices exist. Half-tile or fixed-point choices require a tested downstream schema/mask extension and a new action-resolution identifier.

The expected_card field binds a play request to the card that occupied that hand slot in the observation. This is required for late responses in real-time mode: a stale response must never play a different card that has since moved into the same slot. The runner records requested coordinates, quantized point, engine-submitted point, actual landing point, command-given tick, command-run tick, refusal/acceptance and final action status.

The runner must not replace an invalid action with a different card or a strategically better coordinate. Native engine placement search may relocate a tap exactly as the engine's player-command path does; both requested and actual landing points are logged. This is game semantics, not benchmark strategic assistance.

## 6. Local JSONL subprocess transport

The reference implementation is `royalebench.agents.SubprocessAgent`. It launches one persistent child process per match. The process receives JSON objects, one per stdin line. Standard output is reserved for protocol responses; send logs and diagnostics to standard error.

The process protocol uses these messages:

**Start event** (sent once after launch):
```json
{
  "schema": "royalebench.agent-event.v1",
  "type": "start",
  "match_info": {
    "match_id": "example-match",
    "seat": 0
  }
}
```

The worker must acknowledge startup with:
```json
{"schema":"royalebench.agent-event.v1","type":"ready"}
```

**Decision request**:
```json
{
  "schema": "royalebench.agent-request.v1",
  "type": "act",
  "request_id": "example-match:0:0",
  "decision_id": 0,
  "observation_hash": "64-character-sha256",
  "observation": {}
}
```

The worker returns an `AgentResponseV1` object using the response schema shown above. The action itself must satisfy `ActionV1`.

**End event**: after a completed or void match, the runner sends `royalebench.agent-event.v1` with `type: "end"` and seat-scoped result metadata. No response is expected.

**Close event**: the runner sends `royalebench.agent-event.v1` with `type: "close"`. The worker should exit cleanly. No response is expected.

The subprocess adapter enforces a startup timeout, decision timeout and shutdown grace period. A malformed, stale or timed-out worker response invalidates the match. Credentials are not inherited wholesale from the parent environment: only a small runtime-variable allowlist is inherited. Pass only credentials the participant explicitly intends that worker to receive through the adapter's `env` argument.

The subprocess boundary is a process boundary, **not a complete sandbox**. The child runs with the same user permissions and may have filesystem or network access. Use a separately configured container or OS sandbox for untrusted code submitted by third parties. The in-process Python Agent interface is intended for trusted built-in agents.

A minimal working policy is provided at `examples/agents/hog_cycle_jsonl.py`.

## 7. LLM usage

The intended LLM interface is one decision call per benchmark observation:
- provide the compact current state snapshot, public memory, recent visible events and action schema;
- use a structured JSON/tool-call output format;
- return one action: wait, play(hand_slot, expected_card, x_tile, y_tile), or ability(button);
- validate the response envelope and action;
- execute through the same engine path as every other agent.

Do not require three sequential model calls for strategy, card and placement in the primary track. That unnecessarily adds provider latency and makes systems incomparable. A model may reason hierarchically inside one response.

### Decision cadence profiles

The cadence is part of the versioned tournament profile, not a per-agent preference:
- **fast-250ms-v1:** one decision opportunity every 5 engine ticks (250 ms);
- **llm-api-1s-v1:** one decision opportunity every 20 engine ticks (1 second).

Any agent class may enter either profile. All agents compared in one profile receive the same decision cadence, observation timing and action semantics. Ratings are never pooled across profiles. The 1-second profile reduces API calls for hosted models; it does not provide extra information or a different action interface. Agents can also enter the 250 ms profile if they can sustain its request rate.

At the 250 ms cadence, a three-minute match has up to 720 decision opportunities per seat; at one second it has up to 180. Actual requests can be fewer when the match ends or the agent uses the real-time profile's one-outstanding-request rule.

### Efficient LLM prompting

- Send static game rules, coordinate semantics and fixed deck descriptions at match start, not on every turn.
- Use a compact current snapshot plus the bounded event delta and common public-memory block.
- Keep the current snapshot sufficient to recover after a process restart; do not depend exclusively on a long chat transcript.
- Use provider prompt caching where available, but record model/provider and caching configuration.
- Make one model call per decision. Do not ask the model to explain its reasoning in an extra call.
- Do not expose a strategically curated list of only good placements. The agent outputs a coordinate under the declared action resolution and the engine applies native placement search.

The benchmark does not require a chain-of-thought field. If an agent emits a short explanation, it is diagnostic only and is not scored.

Provider-specific prompt engineering is allowed, but prompts, model identifiers, model versions, sampling settings, tool calls, token usage, cache usage, latency and API cost must be reported.
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
Both agents receive the same decision snapshot and are called concurrently. The engine does not advance until both responses or operational watchdog outcomes are resolved. Latency is measured but does not consume game time. Proposed v1 operational watchdog: 120 seconds per response. A watchdog timeout is recorded as a technical failure/void, not silently converted into an agent loss. Timeout rate and match-completion rate are reported.

### Real-time mode
The engine advances at 1× game speed (one 50 ms game tick per 50 ms wall-clock time). The scheduler offers an observation every 250 ms only when that agent has no outstanding request. Each agent may have at most one in-flight request. The engine never waits for inference. When a response arrives, it is applied at the current engine tick only if the response matches its request and, for a play, the expected_card is still in the named hand slot. Native placement search and command delay then begin at the actual arrival tick. Otherwise the action is rejected as stale/invalid. The agent does not receive another observation while its previous request is outstanding, so slower inference directly reduces its reaction frequency. Report the achieved action rate and end-to-end latency. A 120-second watchdog cancels/invalidates a hung request.

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
