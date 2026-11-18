# RoyaleBench

**A reproducible competitive benchmark for AI agents in Clash Royale-like real-time battles.**

RoyaleBench provides a pinned offline battle environment, player-visible observations, a common agent interface, tournament execution, trajectory export and ratings. Researchers supply a policy: scripted, RL, LLM, or a model-based controller.

## V1 scope

- One canonical simulator: [CRForge](https://github.com/voonhous/crforge), pinned to `fa5959055c590a493d62c8dbc804e602832d08a6` as a submodule.
- One canonical game-data build: `16.635.8`, content SHA `062a11e0500c03cc041f123413b1ef1846b539a4`.
- Fixed mirrored Hog 2.6 deck, equal card/tower levels, deterministic match seeds.
- CRForge's 18 × 32 tile-centre action grid and native PlayerCommands placement semantics.
- MASK_ALL_TILES=1: every tap tile is available for a playable card slot; CRForge retains its own placement search.
- Structured player-visible observations only. Hidden opponent hand, next card, hidden elixir and simulator internals are excluded.
- Paused-clock matches with separate fast-250ms-v1 and llm-api-1s-v1 cadence ratings.
- Random-legal and rule-based baselines, plus a configurable OpenAI-compatible LLM agent.
- Automated match logs, Glicko-2 tournament ratings, and match-level trajectory train/validation/test splits.
- The trajectory dataset is generated automatically by matches; no manually curated training dataset is required.

Visual agents, real-time wall-clock ratings, multi-engine tournaments, deck-building, new RL training and live-game account automation are outside v1.

## Windows setup

Requirements: Git, Python 3.11+, Java 21.

\`\`\`powershell
git clone --recurse-submodules https://github.com/aryandadwal2006/RoyaleBench.git
cd RoyaleBench
.\scripts\bootstrap_upstreams.ps1
.\scripts\build_engine.ps1
\`\`\`

CRForge's game tables are built locally from its configured CDN asset source. Original data tables and game assets are not committed to RoyaleBench.

## Commands

\`\`\`powershell
python -m royalebench config-check
python -m pytest
python -m ruff check src tests
python -m royalebench smoke
python -m royalebench tournament --agents random-legal-v1,hog-cycle-rules-v1 --seeds 11,22
python -m royalebench dataset --matches results/tournament/matches --output results/dataset
\`\`\`

The integrated Windows acceptance script will run tests, a small paired tournament and dataset generation:

\`\`\`powershell
.\scripts\validate_v1.ps1
\`\`\`

## Optional LLM participant

Set credentials in the current PowerShell session. No credentials are written to repository files:

\`\`\`powershell
$env:ROYALEBENCH_LLM_API_KEY = "..."
$env:ROYALEBENCH_LLM_MODEL = "your-model-id"
$env:ROYALEBENCH_LLM_BASE_URL = "https://api.openai.com/v1"
python -m royalebench tournament --agents random-legal-v1,llm --seeds 11,22
\`\`\`

The LLM adapter expects an OpenAI Chat Completions-compatible endpoint and JSON-object output. Configure a model identifier supported by your endpoint. Provider usage and client latency are recorded when returned by the endpoint.

## World-model forecasting baseline

The trajectory exporter creates match-level train/validation/test shards. A persistence baseline can be evaluated on the held-out test shard at multiple decision-interval horizons:

```powershell
python -m royalebench forecast-eval --split results/dataset/test.jsonl.gz --horizons 1,2,4 --output results/forecast-persistence.json
```

The evaluator verifies the dataset manifest and transition observation hashes. Forecast inputs contain the starting observation and intervening actions only. Match outcomes and future observations are withheld from the predictor. The persistence baseline is a sanity reference, not a learned world model; its report is separate from competitive ratings.

## External JSONL agents

External policies can enter tournaments as isolated child processes. A worker receives a versioned `start` event, answers a `ready` handshake, receives one structured observation per `act` request, receives an `end` event with its own match result, and exits on `close`. Standard output is reserved for JSONL protocol messages; write diagnostics to standard error.

A complete example worker is included:

```powershell
python -m royalebench tournament `
  --agents random-legal-v1,external-hog `
  --external-agent-name external-hog `
  --external-agent-command '["python","examples/agents/hog_cycle_jsonl.py"]' `
  --external-agent-cwd . `
  --seeds 11,22,33 `
  --output results/external-agent-tournament
```

For an agent that needs credentials, name only the intended variables in `--external-agent-pass-env`. The parent values are copied into the child explicitly; unrelated environment variables are not inherited:

```powershell
$env:MODEL_API_KEY = "..."
python -m royalebench tournament `
  --agents random-legal-v1,my-agent `
  --external-agent-name my-agent `
  --external-agent-command '["python","worker.py"]' `
  --external-agent-pass-env MODEL_API_KEY
```

This process boundary limits accidental credential exposure and provides startup/decision timeouts, but it is not an OS security sandbox. Do not run untrusted participants under your personal account without an additional container or OS isolation layer.

## Benchmark documentation

- [Architecture and design](docs/ARCHITECTURE.md)
- [Agent protocol](docs/AGENT_PROTOCOL.md)
- [Trajectory dataset and forecasting](docs/DATASET.md)
- [Learned forecaster adapter API](docs/FORECASTER_API.md)
- [Benchmark card and limitations](docs/BENCHMARK_CARD.md)
- [FAIR observation provenance audit](docs/FAIRNESS_AUDIT.md)
- [Implementation roadmap and acceptance gates](docs/ROADMAP.md)

## Repository status

The CRForge adapter, ObservationV1 converter, public-memory cycle tracker, action protocol, baseline agents, concurrent match runner, Glicko-2 ratings, paired tournament runner, OpenAI-compatible LLM adapter, JSONL subprocess adapter, match-level trajectory exporter, tournament provenance manifest and persistence-based multi-horizon forecasting evaluator are implemented. These components still require the final local acceptance run against your installed CRForge build. The persistence predictor is a sanity baseline, not a learned world model. External pretrained checkpoints are not included in the official leaderboard until their observation/action adapters pass compatibility and reproducibility checks.

See [docs/ROADMAP.md](docs/ROADMAP.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Licensing and game data

Upstream source repositories remain pinned as submodules; their source is not copied into the RoyaleBench package. Supercell game tables, graphics, sounds and trademarks are not bundled or relicensed by upstream source licenses. Check upstream notices and applicable game-data use conditions before redistribution.
