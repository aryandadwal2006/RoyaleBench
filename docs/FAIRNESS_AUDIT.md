# FAIR structured-observation audit

**Contract:** ObservationV1  
**Canonical source:** CRForge `VectorEnv` seat observation at commit `fa5959055c590a493d62c8dbc804e602832d08a6`  
**Status:** Converter-level tests pass in CI. The pinned upstream CRForge `:env:test` task completed successfully on Windows on 2026-11-18, but the three RoyaleBench native adapter tests in `tests/test_crforge_native.py` were skipped because the CRForge `installDist` JARs were absent. Final native adapter acceptance is pending.

## Trust boundary

The adapter calls CRForge's seat-specific observation API and passes only that seat's raw observation array and action mask to `build_observation`. The converter reads named fields from the CRForge schema and the entity rows from that same seat view. It does not read a Battle object, the other seat's observation buffer, the opponent's private hand/queue, or the opponent's hidden elixir counter.

CRForge's upstream environment documentation describes its enemy-elixir field as the amount the seat's player counts from visible events, explicitly not the enemy's own hidden count. Its `ElixirCount` logic uses public play costs, regeneration and visible elixir-gain events. The upstream documentation records an exception: champion ability refunds that are not shown to the opponent can make the count drift. The fixed Hog 2.6 v1 deck contains no champion, so that refund path is excluded by the v1 deck configuration. A native integration test must still confirm the configured deck and data version.

## Field-level provenance

| ObservationV1 field | Source | Visibility rule |
|---|---|---|
| `own.elixir`, `own.elixir_reserved` | Seat header `elixir`, `elixir_reserved` | Own state |
| `own.hand`, `own.next_card`, `own.queue` | Seat header `hand_*`, `next_card`, `queue` | Own state only |
| `own.deck`, `own.deck_level`, slot/evolution flags | Seat header `deck*` | Own deck/configuration |
| `own.towers`, `opponent.towers` | Seat header tower HP fields | Public tower health |
| `opponent.estimated_elixir` | Seat header `enemy_elixir` | CRForge's player-side count, not opponent truth |
| `opponent.cards_seen`, cycle and recent plays | `enemy_seen*`, `enemy_play_*`, `enemy_play_count` | Publicly identified enemy plays; unknown card IDs remain null |
| `entities` | `Schema.entities(raw_observation)` | CRForge's seat-filtered visible entity rows |
| `legal_actions` | Seat action mask | Only legal/playable information for this seat |
| `engine` | Schema and game-data metadata | Public runtime provenance |

## Explicitly excluded

ObservationV1 must not contain:
- opponent's true hand slots or hand ordering;
- opponent's true next card or queue;
- opponent's hidden internal elixir value;
- hidden seed or random-generator state;
- raw Battle/World/Player objects, simulator object IDs not exposed in the seat view, or the other seat's observation;
- future states, future actions or match outcome labels.

## Tests currently present

### RoyaleBench tests

- `test_observation_exposes_normalized_elixir_but_not_hidden_state` checks the public observation shape and absence of explicit hidden-state keys.
- `test_observation_is_noninterfering_with_unexposed_hidden_state_fields` changes synthetic hidden fields while holding the seat view fixed and asserts ObservationV1 is unchanged.
- `test_observation_keeps_crforge_raw_scaled_values_for_audit` preserves raw public elixir counts alongside normalized values.
- `test_cycle_is_uncertain_before_four_public_card_plays` and related tests ensure the opponent's hand is not inferred before the public play ledger supports it.

Additional native tests are now present:

- `tests/test_crforge_native.py::test_seat_frames_are_half_turn_transforms_on_native_tower_entities` checks the actual reset observations for both physical king towers in the two seat frames.
- `tests/test_crforge_native.py::test_unseen_opponent_deck_does_not_change_the_other_seats_initial_view` resets the same deterministic match with two different, unobserved opponent decks and compares the receiving seat's entire observation and action mask.
- `tests/test_crforge_native.py::test_hog_v1_public_enemy_elixir_matches_native_truth_during_play` compares the seat-visible opponent-elixir count against CRForge's underlying side state over legal actions in the fixed v1 deck. The native truth is read only by the test, never passed into an agent.
- Adapter startup checks the effective native configuration, mask/id versions and deployment delay. Reset checks the actual decks, per-card levels, mirrored tower HP and initial public-elixir values.
- `tests/test_match_runner.py` verifies a match is classified as an engine fault and voided when either the reset or a later seat observation reports nonzero `entity_overflow`. The runner requires the field to be present and valid rather than silently treating missing metadata as zero.

The acceptance script now runs the pinned CRForge `:env:test` suite before the RoyaleBench Python suite. That upstream suite includes checks for per-seat coordinate transforms and entity visibility, tunnelling trails, hidden spell aim, unrevealed building commands, and enemy-elixir accounting across ordinary spends, visible gains, champion refunds and terminal ticks. In particular, it contains `SeatObservationTest.everyRowReadsTheCoreAndTheTwoSeatsSeeItHalfATurnApart`, `SeatObservationTest.anEnemyTunnellerShowsItsTrailFromTheRunAndItsCardAndPointOnlyWhereItComesUp`, `SeatObservationTest.anEnemySpellFromTheKingShowsItsCardAtTheRunAndItsPointWhereItLands`, `SeatObservationTest.anEnemysHiddenBuildingShowsNothingOfItsCommandAndStaysOnTheScreenLowered`, and the relevant cases in `EnemyElixirCountTest`.

The user ran the pinned CRForge `:env:test` task on Windows on 2026-11-18 and Gradle reported `BUILD SUCCESSFUL`. In the same partial run, the three RoyaleBench tests listed above were skipped because `env/build/install/env/lib` contained no runtime JARs; the run used `-SkipBuild`, which bypassed `:env:installDist`. Thus the upstream native suite completed, but the three native adapter assertions have not yet executed.

## Remaining native acceptance checks

1. Run `.\scripts\validate_v1.ps1` without `-SkipBuild` so `:env:installDist` creates the runtime JARs, then verify all three RoyaleBench native tests execute without skips and the headless tournaments complete.
2. Add a direct native-state mutation test for hidden hand/queue/elixir while preserving the seat-visible state only if the engine exposes a safe and isolated fixture; treat this as additional audit hardening.

Do not mark the native FAIR audit complete until the native and RoyaleBench integration tests pass on the pinned data version.
