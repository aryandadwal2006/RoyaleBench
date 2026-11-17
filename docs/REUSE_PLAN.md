# Upstream Reuse, Copying and Attribution Plan

**Status:** Proposed reuse register. Exact upstream revisions are pinned as submodules under third_party/upstream.

The rule is: keep a complete upstream engine as an upstream dependency; copy only small, identified, independently testable utilities when there is a reason to do so; never copy third-party game data or artwork merely because it is present in an upstream checkout.

## 1. Upstream register

| Project | Pinned revision | Licence checked | RoyaleBench role | Copy policy |
|---|---|---|---|---|
| [voonhous/crforge](https://github.com/voonhous/crforge) | fa5959055c590a493d62c8dbc804e602832d08a6 | Apache-2.0; NOTICE present | Canonical engine candidate, environment, replay/conformance and desktop UI | Keep whole repo as submodule. Do not duplicate the battle core. Maintain only small downstream patch files if necessary. |
| [RoyaleGym/RoyaleGym](https://github.com/RoyaleGym/RoyaleGym) | 278bcb06dae717b89194b992235a9fa8a5209084 | MIT | Reference for fair observations, public memory, cycle tracking, Gym/PettingZoo patterns | Extract/adapt selected memory logic and tests only after compatibility tests against crforge. |
| [RoyaleGym/RoyaleSim](https://github.com/RoyaleGym/RoyaleSim) | a849c29ae632e12f81442c45b0d9b2d2f2f99f15 | MIT for source; data/raw explicitly excluded | Reference for integer-coordinate battle API, placement validation and independent diagnostics | Reference submodule only. Not the v1 official engine. Never copy data/raw. |

These revisions are the latest commits observed during the initial design pass on 2026-11-17. Update only through a reviewed upstream-upgrade ADR and a fresh acceptance/conformance run.

## 2. crforge: reuse as an engine, not as copied source

### Keep as upstream submodule

Retain the repository under third_party/upstream/crforge. The benchmark adapter should consume:
- core battle engine and game-table reader;
- env module, observation schema, action codec and masks;
- conformance module;
- replay reader/writer and replay labeller;
- Python crforge_env wrappers;
- desktop visualizer for manual local testing and human-vs-agent prototypes.

Relevant upstream paths:
- core/ and pathfinding/: battle mechanics and routing; do not fork into RoyaleBench.
- env/src/main/java/org/crforge/env/: Ladder environment, schema, seat visibility, public event tracking and commands.
- conformance/: recorded-trace validation.
- python/crforge_env/: Python adapter, PettingZoo wrapper and schema decoding.
- desktop/: existing interactive visualizer.

### Exact behaviour to preserve

- 50 ms integer ticks.
- PlayerCommands execution path.
- 20-tick command delay in the inspected engine version.
- command reservation/affordability semantics.
- actual native placement search and refusal behaviour.
- per-seat observations and visibility.
- fault/truncation distinction from match loss.
- schema and vocabulary pinning.
- deterministic replay from seed and action history.

### What may need a downstream patch

The current crforge Python action schema uses an 18 × 32 tile-centre grid, four hand slots, wait and ability actions. Higher-resolution placement is not currently part of that public schema.

If the half-tile or fixed-point action extension is accepted, keep it as a small patch under patches/crforge/ with:
- source revision;
- exact changed files;
- rationale;
- tests;
- generated schema-version change;
- expected action count and coordinate mapping.

Do not silently change an upstream schema or reinterpret old checkpoints. Do not claim that a 36 × 64 action space already exists in crforge.

### Attribution

crforge is Apache-2.0. Preserve LICENSE and NOTICE. Its README asks ports/reimplementations to name the original file and commit in a comment at each ported module/function. This request is not a licence condition, but RoyaleBench should follow it whenever it ports any logic. Cite the exact upstream file and commit in source comments and the paper.

crforge NOTICE states that crforge ships no game data; users build tables locally from game files. This is not a licence to redistribute those tables.

## 3. RoyaleGym: selected public-memory and action-interface reference

RoyaleGym is MIT-licensed. Do not import the entire package as the v1 runtime because it is designed around RoyaleSim and its own observation protocol. Port only logic whose semantics can be separated cleanly from its engine adapter.

### Candidate source modules

| Upstream path / symbol | Intended destination | Reuse decision |
|---|---|---|
| royalegym/obs.py: MatchMemory | src/royalebench/observations/memory.py | Candidate for a minimal port; audit dependencies and event timing first. |
| royalegym/obs.py: MatchClock | src/royalebench/observations/clock.py | Port only if its clock law matches the selected crforge release and tests. |
| royalegym/obs.py: fair_fields | src/royalebench/observations/fair_fields.py | Use as a reference for separating direct observation from derived public memory. |
| enemy_possible_hand / enemy_queue_5_8 / enemy_card_cycle | src/royalebench/observations/cycle.py | Adapt the deduction logic; never read the actual opponent hand. |
| opponent elixir counting and elixir_income logic | src/royalebench/observations/elixir.py | Adapt only after deriving exact crforge event semantics, including special income/refunds. |
| tests/test_enemy_queue.py | tests/observations/test_cycle.py | Port/adapt test cases; add crforge differential tests. |
| tests/test_fair_fields.py | tests/observations/test_fairness.py | Use as a model for proving both seats receive mirrored fair observations. |
| tests/test_elixir_income.py | tests/observations/test_elixir.py | Use as a test-design reference. |
| tests/test_press_memory.py | tests/observations/test_abilities.py | Use as a reference for ability-cost bookkeeping. |
| royalegym/action.py: TileActionParser | src/royalebench/actions/ | Reference only for 36 × 64 placement-grid design; do not transplant until crforge coordinate tests pass. |

The initial source-level port must be small. Do not copy all of obs.py or the complete observation builder: it includes RoyaleSim-specific types, state builders and engine adapters.

### Required porting procedure

1. Inspect the exact source at the pinned submodule commit.
2. Identify imports and engine-specific assumptions.
3. Copy the smallest useful function/class set.
4. Retain MIT copyright and permission notices in a third-party notices file and the copied module header.
5. Add a source comment with upstream path, commit and local modifications.
6. Write tests against synthetic event sequences.
7. Run differential tests against crforge's own public observations/replays.
8. Verify the tracker never reads hidden opponent state.
9. Record every semantic difference in docs/observations.md.

## 4. RoyaleSim: coordinate and cross-engine reference only

The RoyaleSim API accepts integer sub-tile coordinates for commands, exposes check_deploy and returns requested/actual command results. This is useful for understanding and testing coordinate interfaces.

It is not the v1 runtime. Never combine a RoyaleSim trajectory and a crforge trajectory as if they share identical mechanics or game tables.

**Critical licence boundary:** RoyaleSim's MIT licence explicitly excludes files under data/raw/, which are reproduced Supercell game-data tables. Do not vendor, redistribute, or treat those files as MIT-licensed. Its code licence does not override the provenance or rights of game data.

## 5. Other repositories reviewed

These remain research references, not v1 dependencies.

| Repository | Relevant idea | Reuse decision |
|---|---|---|
| Hasty-CR | Compact simulator, scripted policy, behaviour cloning, PPO, action diagnostics | MIT licence observed. Consider a baseline only after its mechanics are mapped to the canonical engine. Do not import its simulator. |
| ClashAI | Replay imitation, PPO, frozen opponent league, held-out evaluation, specialist/generalist analysis | No root LICENSE was found in the inspected lookup. Do not copy code until a clear licence is verified. Methods may be independently implemented and cited. |
| FirstLight_CR | Recurrent entity/relation policy, action hierarchy, IL/PPO and league ideas | No root LICENSE was found in the inspected lookup. Do not copy source without a clear licence or permission. |
| clash-jev | Structured, hierarchical LLM choice interface and latency logging | MIT licence observed. Do not import its live Android/ADB automation path. Use the offline benchmark only. |
| MSU-AI/clash-royale-gym | Minimal Gymnasium wrapper | MIT licence observed; README warns its initial version used mock API calls. No v1 dependency. |
| KataCR | Vision and offline-RL research reference | Review separately before any code reuse; not a v1 runtime dependency. |

Prior discussions of architecture are not sufficient to establish a source-code licence. Before copying any code, inspect the exact upstream LICENSE, NOTICE and file headers.

## 6. Third-party notices and source provenance

Create and maintain:
- THIRD_PARTY_NOTICES.md: project, URL, pinned revision, licence, copyright, files copied and local changes.
- patches/crforge/: patch files against an exact crforge revision, each with tests.
- source comments on every copied/ported crforge function/module.
- docs/upstream-upgrades/: compatibility and conformance evidence for each engine upgrade.

A submodule is a pinned source reference, not permission to relicense its contents. Keep upstream licence files available and do not present third-party code as original RoyaleBench work.

## 7. Data, replay and game-brand boundary

Do not place the following in RoyaleBench source or release artifacts without separately confirmed rights:
- Supercell game-data tables;
- original Clash Royale sprites, UI art, sound, music or videos;
- replay files scraped from third-party datasets without verifying their licence and redistribution terms;
- account data or private player information.

crforge requires users to build game tables locally and its NOTICE says it ships no game data. RoyaleSim's MIT licence excludes data/raw. Public availability of a replay or asset is not itself permission to redistribute it.

The benchmark should prefer synthetic scenario manifests, original visual assets, public APIs with permitted use, and user-local engine table setup. Legal/provenance review is a release gate.

## 8. Upstream update policy

Never float upstream dependencies on main/latest in an official benchmark run. Each benchmark release pins exact commits and data hashes. An update requires:
- source diff review;
- licence and data-provenance recheck;
- engine test suite;
- reference-trace conformance report;
- action-placement regression tests;
- fair-observation/no-leak tests;
- public-memory differential tests;
- replay compatibility report;
- benchmark version bump and migration note.
