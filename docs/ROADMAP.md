# RoyaleBench v1 Implementation Status

**Status:** Core benchmark implementation is in place; final local CRForge acceptance and research evaluation remain outstanding.

This roadmap distinguishes code that exists from evidence that it has been validated against the pinned native engine. A checked implementation item does not imply that the user's Windows installation or the upstream CRForge test suite has passed.

## Frozen v1 scope

- One canonical engine: CRForge commit `fa5959055c590a493d62c8dbc804e602832d08a6`.
- Game-data version: `16.635.8`, with its local content SHA recorded in match manifests.
- Fixed mirrored Hog 2.6 deck, card/tower level 11.
- CRForge 18 x 32 tile-centre action grid, `MASK_ALL_TILES=1`, native PlayerCommands placement.
- FAIR structured observation only; opponent hand/queue/elixir are not read from privileged engine state.
- Two paused-clock strategic cadence profiles: 5 and 20 CRForge ticks.
- In-process baseline/LLM agents and isolated JSONL subprocess participants.
- Paired seat-swapped tournaments, Glicko-2 ratings, match logs and automatic trajectory export.
- World-model forecasting uses an independent evaluation interface and is not mixed with competitive agent ratings.

Visual agents, real-time wall-clock competition, deck construction, alternate-engine rankings, half-tile actions, live-game account automation and training a new RL policy are outside v1.

## Implemented components

### Repository, engine adapter and configuration

- [x] Pin CRForge, RoyaleGym and RoyaleSim upstream revisions as submodules.
- [x] Add Windows bootstrap and CRForge environment-build scripts.
- [x] Freeze the mirrored Hog 2.6 v1 configuration and both decision profiles.
- [x] Implement the Python adapter around CRForge `VectorBattle`.
- [x] Validate engine data version, 18 x 32 action grid, and `MASK_ALL_TILES` at initialization.
- [x] Resolve configured deck labels to exact upstream vocabulary rows.
- [ ] Run the headless adapter on the user's local Windows installation.
- [ ] Record the local build's exact upstream test failures and decide which affect v1.

### Observation and action contracts

- [x] Add ActionV1 and AgentResponseV1 JSON Schemas and typed Python validators.
- [x] Add ObservationV1 conversion from CRForge's seat-visible arrays.
- [x] Use seat-relative entity side and coordinates supplied by CRForge's observation writer.
- [x] Expose hand, public deck, visible entities/effects, towers, public events and legal action masks.
- [x] Track opponent card-cycle deductions from CRForge's newest-first public play ledger.
- [x] Preserve unknown card identities and decline exact-hand inference when the latest four public plays are not all known and distinct.
- [x] Validate hand-slot identity before encoding a play action.
- [x] Reject invalid coordinates; do not silently snap or repair agent actions.
- [x] Keep native placement search and command delay in CRForge.
- [x] Document field-level FAIR information provenance and converter-level hidden-field noninterference tests.
- [ ] Complete two-seat hidden-state leakage and seat-frame tests against the native CRForge engine.
- [ ] Add differential tests for opponent elixir estimation, including unsupported refunds/income mechanics.
- [ ] Verify both seat coordinate transforms and the selected deck's placement mechanics against live CRForge runs.

### Agent SDK and execution

- [x] Define the in-process Python Agent lifecycle.
- [x] Implement no-op, random-legal and transparent Hog-cycle rule baselines.
- [x] Implement an OpenAI-compatible structured JSON-action agent.
- [x] Implement a persistent JSONL subprocess transport with startup handshake, request identity, response validation and match-end event.
- [x] Give child processes a restricted inherited environment; pass selected participant credentials explicitly.
- [x] Add startup, decision and shutdown timeouts; terminate a timed-out worker process tree.
- [x] Add an external-lab example worker.
- [x] Allow an external JSONL participant in CLI tournaments.
- [ ] Add a container isolation runner before accepting untrusted public submissions. The current subprocess boundary is not a security sandbox.
- [ ] Integrate FirstLight or Hasty pretrained weights only after exact observation/action compatibility and licensing checks.
- [ ] Do not list external checkpoints on a leaderboard until their adapters pass reproducibility tests.

### Match runner and tournament

- [x] Run two agents concurrently at identical simulated decision ticks.
- [x] Deep-copy each seat observation before passing it to an agent.
- [x] Apply a shared per-decision response deadline.
- [x] Separate agent exceptions, invalid actions, engine faults and incomplete matches.
- [x] Record request/action details, observations, next observations, match manifests and results.
- [x] Record per-agent latency distributions.
- [x] Implement round-robin matches with paired seat swaps and deterministic seeds.
- [x] Implement Glicko-2 with frozen pre-period opponent ratings.
- [x] Compute a seed-cluster bootstrap interval for aggregate score.
- [x] Add a top-level tournament provenance manifest with hashes for match manifests and summary artifacts.
- [ ] Add canonical replay fingerprints (the pinned engine adapter does not yet expose a stable replay artifact hash).
- [x] Add tests for seat-scoped match-end callbacks and watchdog cancellation through the runner.
- [ ] Validate rankings, W/D/L counts and rating period semantics on actual CRForge matches.

### Trajectory dataset and world-model evaluation

- [x] Record per-seat observation/action/next-observation transitions during every completed match.
- [x] Export compressed JSONL train/validation/test splits.
- [x] Group split assignment by simulator seed so paired seat-swapped matches cannot leak across splits.
- [x] Record data provenance, split membership, transition counts and SHA-256 hashes.
- [x] Make gzip output deterministic and prevent accidental overwrite of an existing dataset.
- [x] Define ForecastRequestV1 and ForecastResponseV1 schemas bound to observation hashes and forecast horizons.
- [x] Implement a persistence baseline and action-conditioned multi-horizon forecasting evaluator.
- [x] Implement multi-horizon metrics for visible tower HP, elixir, entity-type precision/recall/F1 and entity-count error, skipping missing numeric fields.
- [x] Add held-out prediction evaluation CLI and JSON report generation.
- [x] Keep outcomes and future observations outside the predictor call; test the action-prefix input contract.
- [x] Verify the dataset shard against its manifest SHA-256 and validate source/target observation hashes before forecasting.

## Remaining release work

1. Add a documented learned-predictor adapter entry point and broaden forecasting metrics to entity identity, movement and event timing where CRForge exposes reliable stable identifiers.
2. Complete the native two-seat FAIR audit and verify opponent-elixir accounting under the exact fixed v1 deck.
3. Reconcile FirstLight and Hasty policies: inspect pinned source, checkpoint availability, licences, input/output semantics and card/version compatibility. If adaptation is not defensible, document them as external references rather than forcing them into v1.
4. Add canonical replay/result fingerprints and paper-ready CSV/JSON summaries.
5. Add container isolation before accepting untrusted public submissions; the current subprocess boundary is not a security sandbox.
6. Update the benchmark card and paper methods to reflect only implemented behaviour.
7. Run the integrated Windows validation script once the implementation is frozen.
8. Run a preregistered/pinned final tournament with enough independent seeds for meaningful uncertainty.
9. Generate the paper's result tables, figures and limitations from saved artifacts.

## Final Windows acceptance

Run once after pulling the completed implementation:

```powershell
python -m pip install -e ".[dev,engine]"
python -m pip install -e .\third_party\upstream\crforge\python
.\scripts\validate_v1.ps1 -SkipBuild
```

The integrated script must finish with:
- Python tests passing.
- Ruff passing.
- V1 config validation passing.
- Real headless CRForge matches completing for both seats.
- Tournament summary and per-match manifests/results written.
- Non-empty train, validation and test trajectory splits with a valid dataset manifest.
- A single validation report recording software versions, engine version/hash, match counts, split counts and output paths.

The user's desktop visualizer run establishes that the CRForge desktop runtime starts and supports manual play. It does not substitute for this headless acceptance test. The user's earlier note that some upstream tests failed remains unresolved until their test log is inspected.

## Release definition

RoyaleBench v1 is complete only when the core implementation above passes the local integration gates, its tournament protocol is reproducible, the FAIR observation contract is tested, and the paper's claims match the generated evidence. The roadmap intentionally does not require visual, real-time, multi-engine, deck-building or large-scale training infrastructure.
