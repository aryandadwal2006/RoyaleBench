# Planned Repository Structure

This is the target source layout. Directories are added when their phase begins; the diagram is a plan, not a claim that the modules are already implemented.

```text
RoyaleBench/
├── README.md
├── pyproject.toml
├── .gitmodules
├── .gitignore
├── LICENSE                         # choose only after project-wide licence review
├── THIRD_PARTY_NOTICES.md
│
├── docs/
│   ├── ARCHITECTURE.md
│   ├── AGENT_PROTOCOL.md
│   ├── REUSE_PLAN.md
│   ├── REPO_STRUCTURE.md
│   ├── ROADMAP.md
│   ├── DECISIONS.md
│   ├── observations/
│   │   ├── FAIR_FIELDS.md
│   │   ├── PUBLIC_MEMORY.md
│   │   └── VISUAL_TRACK.md
│   ├── evaluation/
│   │   ├── STRATEGIC_STRENGTH.md
│   │   ├── REAL_TIME.md
│   │   └── WORLD_MODEL_FORECAST.md
│   └── upstream-upgrades/
│
├── third_party/
│   ├── README.md
│   └── upstream/                   # pinned Git submodules, not copied source
│       ├── crforge/
│       ├── royalegym/
│       └── royalesim/
│
├── patches/
│   └── crforge/                    # small, reviewable patch files only
│
├── schemas/
│   ├── action.v1.schema.json
│   ├── agent-response.v1.schema.json
│   ├── observation.v1.schema.json  # add after field registry is tested
│   ├── world-model-request.v1.schema.json  # add after predictor contract is frozen
│   ├── agent-metadata.v1.schema.json
│   └── match-manifest.v1.schema.json
│
├── configs/
│   ├── engine/
│   ├── decks/
│   ├── action-resolution/
│   ├── tournaments/
│   └── agents/
│
├── src/
│   └── royalebench/
│       ├── __init__.py
│       ├── protocol/                # initial implementation exists
│       │   ├── actions.py
│       │   ├── responses.py
│       │   ├── types.py
│       │   ├── validation.py
│       │   ├── serialization.py
│       │   └── versions.py
│       │
│       ├── engine/
│       │   ├── base.py
│       │   └── crforge/
│       │       ├── adapter.py
│       │       ├── schema.py
│       │       ├── actions.py
│       │       ├── observations.py
│       │       └── capabilities.py
│       │
│       ├── observations/
│       │   ├── fair.py
│       │   ├── events.py
│       │   ├── memory.py
│       │   ├── cycle.py
│       │   ├── elixir.py
│       │   └── visual.py
│       │
│       ├── actions/
│       │   ├── types.py
│       │   ├── coordinates.py
│       │   ├── placement.py
│       │   ├── validation.py
│       │   └── resolutions.py
│       │
│       ├── agents/
│       │   ├── base.py
│       │   ├── registry.py
│       │   ├── runner.py
│       │   ├── local.py
│       │   ├── container.py
│       │   └── remote.py
│       │
│       ├── llm/
│       │   ├── prompt.py
│       │   ├── structured_output.py
│       │   ├── providers/
│       │   └── telemetry.py
│       │
│       ├── world_models/
│       │   ├── predictor.py
│       │   ├── forecast.py
│       │   ├── opponent.py
│       │   └── adapters/
│       │
│       ├── planning/
│       │   ├── candidates.py
│       │   ├── mpc.py
│       │   ├── scoring.py
│       │   └── opponent_population.py
│       │
│       ├── tournament/
│       │   ├── schedule.py
│       │   ├── seeds.py
│       │   ├── match.py
│       │   ├── pairing.py
│       │   └── ratings.py
│       │
│       ├── latency/
│       │   ├── lockstep.py
│       │   ├── realtime.py
│       │   ├── deadlines.py
│       │   └── telemetry.py
│       │
│       ├── evaluation/
│       │   ├── matches.py
│       │   ├── prediction.py
│       │   ├── counterfactual.py
│       │   ├── planning_regret.py
│       │   └── statistics.py
│       │
│       ├── replay/
│       │   ├── manifest.py
│       │   ├── writer.py
│       │   └── reader.py
│       │
│       └── visualization/
│           ├── crforge_desktop.py
│           └── render_contract.py
│
├── examples/
│   ├── agents/
│   │   ├── random_agent.py
│   │   ├── scripted_agent.py
│   │   └── external_lab_template/
│   ├── llm/
│   └── world_model/
│
├── tests/
│   ├── test_protocol_actions.py   # implemented
│   ├── test_protocol_responses.py # implemented
│   ├── protocol/
│   ├── engine/
│   ├── observations/
│   ├── actions/
│   ├── agents/
│   ├── latency/
│   ├── tournament/
│   ├── evaluation/
│   ├── determinism/
│   └── no_leak/
│
├── scripts/
│   ├── check_upstreams.sh
│   ├── run_acceptance.sh
│   ├── run_tournament.py
│   └── inspect_replay.py
│
└── artifacts/                      # generated locally; do not commit large runs
    ├── matches/
    ├── replays/
    ├── reports/
    └── checkpoints/
```

## Ownership boundaries

| Package | Owns | Must not own |
|---|---|---|
| engine/crforge | Engine startup, configuration, schema decode, step/reset, native action execution | Agent strategy, rating, prompt design |
| observations | FAIR state, visible events, public memory and modality transforms | Hidden opponent state |
| actions | Versioned action types, coordinate transforms, placement resolution and validation | Strategic repair of agent actions |
| agents | Lab-facing lifecycle and process/container/HTTP execution | Engine process or opponent process access |
| llm | Optional LLM provider and structured-output adapters | Special game privileges or different action semantics |
| world_models | Predictor registration and forecast adapter | Claiming a predictor is a player without a controller |
| planning | Shared candidate generator, MPC and scoring interfaces | Reading hidden future state |
| tournament | Pairing, hidden seeds, manifests and ratings | Model-specific performance claims |
| latency | Paused-clock and real-time schedulers and telemetry | Backdating late actions |
| evaluation | Match, prediction, counterfactual and statistical metrics | Combining incomparable leaderboards |
| replay | Durable match/event logs and replay metadata | Committing private or unlicensed replay corpora |

## Minimal v1 implementation subset

Do not implement the entire planned tree at once. V1 needs only:
- engine/crforge;
- protocol types/validation;
- observations/fair/events/memory/cycle/elixir;
- actions/types/coordinates/resolutions;
- agents/base/local;
- tournament/match/pairing/seeds/ratings;
- latency/lockstep;
- evaluation/matches/statistics;
- replay/manifest/writer;
- tests for engine, fairness, action resolution, determinism and no-leak.

The LLM package can initially be an example agent outside the benchmark core. The world-model package begins with a protocol and evaluation harness, not a library of third-party pretrained models.
