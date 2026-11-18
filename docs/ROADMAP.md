# RoyaleBench v1 Implementation Status

**Status:** Core benchmark implementation is in place. The upstream CRForge Gradle test task has passed on the user's Windows machine; final headless adapter acceptance and research evaluation remain outstanding.

This roadmap distinguishes implementation status from validation evidence against the pinned native engine. A checked implementation item records that the code exists; only the explicitly recorded acceptance results below count as native-runtime evidence.

## Frozen v1 scope

- One canonical engine: CRForge commit `fa5959055c590a493d62c8dbc804e602832d08a6`.
- Game-data version: `16.635.8`, content SHA `062a11e0500c03cc041f123413b1ef1846b539a4`, verified at engine startup and recorded in match manifests.
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
- [x] Freeze the exact mirrored Hog 2.6 deck and ordering, CRForge source commit, game-data content SHA, levels, tick limit, mask/action semantics and both decision profiles.
- [x] Implement the Python adapter around CRForge `VectorBattle`.
- [x] Verify the actual CRForge source checkout commit and exact game-data content SHA at initialization.
- [x] Validate engine data version, 18 x 32 action grid, and `MASK_ALL_TILES` at initialization.
- [x] Validate effective CRForge cadence, card/tower levels, tick limit, mask and entity-ID versions, and native 20-tick command delay against v1 at startup.
- [x] Validate the actual reset deck, card levels, symmetric tower HP and initial public-elixir values for both seats.
- [x] Resolve configured deck labels to exact upstream vocabulary rows.
- [x] Add regression tests for source-commit verification, data-version/content-SHA checks and runtime/reset configuration gates.
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
- [x] Add native CRForge integration tests for seat-frame transforms, unseen-opponent-deck noninterference and v1 enemy-elixir accounting.
- [x] Void matches if either seat reports omitted visible entities (`entity_overflow > 0`); reject missing or invalid overflow metadata.
- [x] Test match voiding for overflow in reset and later observations.
- [x] Wire the pinned upstream `:env:test` observation/elixir suite into final Windows acceptance.
- [x] Execute the pinned upstream CRForge `:env:test` task on Windows (2026-11-18; Gradle reported `BUILD SUCCESSFUL`).
- [ ] Execute RoyaleBench's three native Python integration tests against the installed CRForge distribution; they were skipped in the partial run because `-SkipBuild` left `env/build/install/env` without runtime JARs.
- [ ] Consider a direct hidden hand/queue/elixir mutation fixture if the native engine exposes a safe isolated fixture; this is additional audit hardening, not a reason to expand v1 scope.

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
- [x] Implement multi-horizon metrics for visible tower HP, elixir, entity-type counts, stable entity-ID precision/recall/F1, matched-entity position error, visible entity HP and entity-count error, skipping unavailable values.
- [x] Validate trajectory decision continuity, seat/match identity, engine-tick intervals and chained observation hashes before forecasting.
- [x] Document the Python Forecaster protocol so learned checkpoints can be adapted without adding their training stack to RoyaleBench.
- [x] Add held-out prediction evaluation CLI and JSON report generation.
- [x] Keep outcomes and future observations outside the predictor call; test the action-prefix input contract.
- [x] Verify the dataset shard against its manifest SHA-256 and validate source/target observation hashes before forecasting.

## Remaining release and paper-evaluation work

1. Complete the Windows integrated acceptance run so the three RoyaleBench native CRForge tests execute rather than skip, and both headless tournaments, dataset export and forecasting evaluation finish.
2. Add forecast event-timing metrics only if they are central to the paper's stated world-model contribution; otherwise keep the persistence evaluator as a sanity baseline and do not expand v1.
3. Reconcile FirstLight and Hasty policies only if a lossless ObservationV1/ActionV1 adapter, compatible game version, checkpoint provenance and licence can be established. Otherwise retain them as related-work references, not leaderboard baselines.
4. Run a pinned paper evaluation with substantially more independent seed groups than the three-seed acceptance smoke test. Report W/D/L, seat-swap results, Glicko-2 rating deviation, seed-cluster uncertainty, failures and voids.
5. Include at least one actual learned or hosted-model participant if the paper makes claims about learned/LLM agents. An adapter existing in the repository is not empirical evidence.
6. Generate paper tables and figures from saved tournament artifacts; freeze model IDs, prompts, decoding settings and provider configuration for any hosted-model results.
7. Treat canonical replay fingerprints and container isolation as release hardening only if needed by the chosen submission or public-submission threat model. They are not prerequisites for drafting the v1 paper.

## Final Windows acceptance

After pulling the current `main`, run the complete first-time acceptance path:

```powershell
git pull origin main
.\scripts\validate_v1.ps1
```

This path bootstraps the pinned submodules and invokes `build_engine.ps1`, which runs CRForge `:env:installDist` and `:tables:dataVersionTables`. The installed `env/build/install/env/lib` JARs are required by the headless Python adapter. The upstream `:env:test` task passing does **not** create that install distribution.

Use `-SkipBuild` only after a successful engine build has already created the runtime JARs and game tables:

```powershell
.\scripts\validate_v1.ps1 -SkipBuild
```

A complete run must finish with:
- Pinned CRForge `:env:test` native environment suite passing.
- All RoyaleBench Python tests passing; the JUnit report must show at least three native CRForge integration tests collected and zero skipped.
- Ruff and v1 configuration validation passing.
- Real headless CRForge matches completing for both seats in the paired baseline tournament and the external JSONL-worker tournament.
- Non-empty train, validation and test trajectory splits with a valid dataset manifest and hashes.
- Held-out persistence forecasting completing at horizons 1, 2 and 4.
- A validation report recording software versions, engine version/hash, match counts, split counts and output paths, alongside the pytest JUnit report.

### Observed partial Windows run (2026-11-18)

The subsequent bootstrap-script fix was validated by a dedicated Windows GitHub Actions job: all three PowerShell scripts parsed, and the script cloned/verified the three pinned upstream submodules successfully. The user's local full engine build and headless tournament acceptance are still outstanding.


The user's run used Python 3.14.5, Java 21.0.13 and `-SkipBuild`. The pinned CRForge `:env:test` task completed with Gradle `BUILD SUCCESSFUL`; RoyaleBench's Python suite reported 114 passed and 3 skipped; Ruff and `config-check` passed. The three skips were `tests/test_crforge_native.py`, because the CRForge install distribution was absent. The first tournament then stopped before any match because no JARs existed under `env/build/install/env/lib`. This is an incomplete build/acceptance run, not evidence of a match-runner or agent failure. The validation script now checks for the missing runtime distribution and reports the required build command before entering the Python integration tests.

The user's desktop visualizer run establishes that the CRForge desktop runtime starts and supports manual play. It does not substitute for headless adapter acceptance.

The detailed ICML 2027 research and implementation plan is maintained at the repository root in [plan.md](../plan.md). This roadmap remains the implementation-status record; the plan defines the research additions and paper schedule.

## Paper drafting readiness

The non-empirical paper sections can be drafted now: motivation, related work, benchmark design, observation/action contracts, simulator integration, tournament protocol, dataset construction and limitations. Keep the results section provisional until the complete local acceptance run and a larger frozen evaluation have finished.

Keep claims aligned with the implemented v1: one pinned CRForge build and game-data fingerprint, one mirrored Hog 2.6 deck at equal levels, structured FAIR observations, an 18 × 32 tile-centre action interface and paused-clock decision cadences. The persistence predictor is a sanity baseline, not a trained world model. Do not claim multi-deck, multi-engine, visual-agent, real-time or broad strategic-intelligence coverage. Treat RoyaleGym/RoyaleSim and other Clash Royale environments as related work rather than claiming RoyaleBench is the first such environment.

## Release definition

RoyaleBench v1 is complete only when the core implementation above passes the local integration gates, its tournament protocol is reproducible, the FAIR observation contract is tested, and the paper's claims match the generated evidence. The roadmap intentionally does not require visual, real-time, multi-engine, deck-building or large-scale training infrastructure.
