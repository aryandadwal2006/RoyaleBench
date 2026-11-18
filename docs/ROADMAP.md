# RoyaleBench v1 Implementation Status

**Status:** Frozen v1 implementation and complete local Windows integration acceptance passed on 2026-11-18. The run executed the native adapter tests, both headless tournament paths, trajectory export and persistence forecasting. Research-grade evaluation and the ICML research extensions remain outstanding.

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
- [x] Run the headless adapter on the user's local Windows installation against the pinned CRForge install and game tables (2026-11-18).
- [x] Resolve and document the Windows JDK/JPype discovery, canonical CRForge card-row mapping and PowerShell external-command serialization issues encountered during acceptance.

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
- [x] Execute all three RoyaleBench native Python integration tests against the installed CRForge distribution (2026-11-18; 3 collected, 0 skipped).
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
- [x] Verify paired seat-swapped match execution and W/D/L/result recording on actual CRForge matches in the three-seed smoke acceptance run.
- [ ] Validate strategic ranking quality, uncertainty calibration and rating-period semantics on a larger, pre-registered evaluation. Smoke-test rankings are not research evidence.

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

1. Complete WP1: finish the related-work matrix, one-page novelty memo, research questions/hypotheses, deck-fidelity choices and statistical protocol before expanding the experiment matrix.
2. Investigate the smoke-run baseline ordering. Random-legal won 5/6 matches against the in-process Hog-cycle policy and 6/6 against the external Hog worker. Treat these as diagnostic observations, not strategic conclusions; verify policy behavior and parity first.
3. Add a separately versioned research configuration with at least three engine-verified deck archetypes and a paired mirror/cross-matchup schedule. Do not alter the frozen v1 deck or retroactively reinterpret its results.
4. Implement deterministic seed-plus-action-prefix reconstruction and the counterfactual candidate-set regret diagnostic. Verify exact observation hashes and ticks before making action-quality claims.
5. Add deck-aware heuristics, compact imitation/PPO/search baselines, and hosted LLM/VLM comparisons only where they test explicit hypotheses and can be reproduced.
6. Run a pilot to estimate seed-cluster variance, then freeze a substantially larger paper evaluation with paired agent-difference intervals, W/D/L, seat effects, ratings, failures and voids.
7. Generate paper tables and figures from frozen artifacts. Keep the persistence forecaster a sanity baseline unless a learned world model supports a specific claim.
8. Treat canonical replay fingerprints and container isolation as release hardening only if required by the submission or public-submission threat model.

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

### Historical partial Windows runs (2026-11-18)

The earlier partial attempts exposed and led to fixes for four issues: the `-SkipBuild` run lacked the `:env:installDist` JARs; JPype could not discover `jvm.dll` from `java.exe` alone; the pinned game tables used the internal `IceGolemite` row for the public `IceGolem` card name; and Windows PowerShell stripped the quotes from an inline JSON worker command. These failures were resolved before the successful acceptance run below.

The current validation script resolves `JAVA_HOME`, verifies JPype's JVM path, uses the exact pinned CRForge deck-row aliases, and passes external worker argv through a UTF-8 JSON file.

The detailed ICML 2027 research and implementation plan is maintained at the repository root in [plan.md](../plan.md). This roadmap remains the implementation-status record; the plan defines the research additions and paper schedule.

### Successful local Windows acceptance (2026-11-18)

The user completed `.\\scripts\\validate_v1.ps1 -SkipBuild` on Windows using Python 3.14.5 and Java 21.0.13. The consolidated report is in the local run directory `results/validation-20261118-171426/validation_report.json`.

- Pinned CRForge `:env:test`: `BUILD SUCCESSFUL`; six runtime JARs and game-data tables were present.
- Python: **120 passed**; all 3 native CRForge adapter tests executed, 0 skipped.
- Ruff: all checks passed. Frozen v1 config check: passed.
- Paired baseline tournament: **6/6 completed**, 0 void/failed.
- External JSONL worker tournament: **6/6 completed**, 0 void/failed.
- Dataset: 6 matches, 3 seed-cluster splits; train 3,556 transitions, validation 2,948, test 2,996. Manifest and shard hashes were generated.
- Persistence forecast: horizons 1, 2 and 4 completed with 2,996, 2,992 and 2,984 examples respectively.
- Final script status: `VALIDATION PASSED`.

The default tournaments are only a three-seed smoke test. Random-legal won 5/6 against the in-process Hog-cycle agent and 6/6 against the external Hog worker. This surprising ordering warrants a baseline-behavior/parity audit before any agent-strength interpretation. It does not invalidate the integration acceptance, whose purpose is to verify that matches and outputs complete.


The non-empirical paper sections can be drafted now: motivation, related work, benchmark design, observation/action contracts, simulator integration, tournament protocol, dataset construction and limitations. The complete local acceptance run is done; keep results claims provisional until a larger, frozen research evaluation has finished.

Keep claims aligned with the implemented v1: one pinned CRForge build and game-data fingerprint, one mirrored Hog 2.6 deck at equal levels, structured FAIR observations, an 18 × 32 tile-centre action interface and paused-clock decision cadences. The persistence predictor is a sanity baseline, not a trained world model. Do not claim multi-deck, multi-engine, visual-agent, real-time or broad strategic-intelligence coverage. Treat RoyaleGym/RoyaleSim and other Clash Royale environments as related work rather than claiming RoyaleBench is the first such environment.

## Release definition

RoyaleBench v1 is complete only when the core implementation above passes the local integration gates, its tournament protocol is reproducible, the FAIR observation contract is tested, and the paper's claims match the generated evidence. The roadmap intentionally does not require visual, real-time, multi-engine, deck-building or large-scale training infrastructure.
