# Windows integrated validation

**Purpose:** verify that the frozen RoyaleBench v1 implementation runs end to end against the pinned CRForge engine on Windows. A successful acceptance run is a software integration check, not the final statistical evaluation for a research paper.

## Requirements

- Git with submodule support
- Python 3.11 or newer
- Java 21
- Network access for the pinned upstream bootstrap and CRForge game-table download on the first build

## First-time run

From the repository root, after pulling the current main branch:

```powershell
git pull origin main
.\scripts\validate_v1.ps1
```

The script performs the complete setup and acceptance path:

1. Synchronizes and verifies the pinned upstream submodules.
2. Builds the CRForge `:env:installDist` runtime distribution and game tables.
3. Installs the RoyaleBench and pinned CRForge Python packages.
4. Runs the pinned CRForge Gradle `:env:test` suite.
5. Runs RoyaleBench's Python tests and Ruff. The JUnit report is checked so all three native CRForge adapter tests must execute without skips.
6. Checks the frozen v1 configuration.
7. Runs the paired random-legal versus Hog-cycle baseline tournament.
8. Runs the external JSONL worker integration tournament.
9. Exports match-level trajectory train/validation/test shards.
10. Runs the held-out persistence forecaster at decision horizons 1, 2 and 4.
11. Checks the manifests and writes a consolidated validation report.

The default acceptance seeds are `11,22,33` and the default profile is `fast-250ms-v1`.

## Repeated run without rebuilding

Use this only after `scripts/build_engine.ps1` has completed successfully and the CRForge install distribution and game tables remain available:

```powershell
.\scripts\validate_v1.ps1 -SkipBuild
```

The switch skips the upstream bootstrap and `:env:installDist` build. It does not make a missing CRForge runtime usable. The headless adapter loads JAR files from:

```
third_party/upstream/crforge/env/build/install/env/lib/
```

The pinned game tables are expected under:

```
%USERPROFILE%\.crforge\tables\16.635.8
```

The validation script checks for the runtime JARs and game tables before starting the RoyaleBench Python integration suite. The Gradle `:env:test` task builds/runs upstream tests but does **not** create the `:env:installDist` distribution. A successful Gradle test task is therefore not a substitute for the installed runtime.

## Interpreting the 2026-11-18 partial run

The observed Windows run used Python 3.14.5, Java 21.0.13 and the `-SkipBuild` switch. The pinned CRForge `:env:test` task completed with `BUILD SUCCESSFUL`; the Python suite reported 114 passed and 3 skipped; Ruff and `config-check` passed. The three skipped tests were RoyaleBench's native adapter tests in `tests/test_crforge_native.py`, because the CRForge install distribution was absent. The headless tournament then stopped before starting a match because no JARs existed in `env/build/install/env/lib`.

No tournament match, trajectory dataset or forecast was produced by that partial run. It does not establish full v1 acceptance. Run the first-time command above without `-SkipBuild`.

## Outputs

Each run writes to a timestamped directory under `results/validation-YYYYMMDD-HHMMSS/`, including:

- `validation_report.json`
- `pytest-junit.xml`
- CRForge's Gradle HTML test report at `third_party/upstream/crforge/env/build/reports/tests/test/index.html`, including an explicit zero-skip gate for the native adapter tests
- paired baseline tournament output
- external JSONL-agent tournament output
- `trajectory_dataset/` with three compressed splits and a manifest
- `forecast-persistence.json`

Keep the entire run directory as an acceptance artifact. Do not hand-edit the generated manifest or report.

## Acceptance versus paper evaluation

The three default seeds are a small smoke/acceptance set. They are only intended to verify that both seats, the agent protocol, the trajectory exporter and the forecast evaluator work end to end. They are not enough for stable ranking claims or paper-grade uncertainty estimates.

For the paper, run a separately frozen, larger set of independent seed groups and report win/draw/loss counts, seat-swapped outcomes, Glicko-2 ratings with rating deviation, seed-cluster uncertainty, voids/failures, and exact engine/data fingerprints. If reporting learned or hosted-model results, freeze the model identifier, prompt, decoding configuration and provider settings. See [ROADMAP.md](ROADMAP.md) and [BENCHMARK_CARD.md](BENCHMARK_CARD.md).
