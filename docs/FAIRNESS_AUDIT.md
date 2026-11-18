# FAIR structured-observation audit

**Contract:** ObservationV1  
**Canonical source:** CRForge `VectorEnv` seat observation at commit `fa5959055c590a493d62c8dbc804e602832d08a6`  
**Status:** Converter-level noninterference tests exist; final two-seat native-engine audit remains an acceptance gate.

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

- `test_observation_exposes_normalized_elixir_but_not_hidden_state` checks the public observation shape and absence of explicit hidden-state keys.
- `test_observation_is_noninterfering_with_unexposed_hidden_state_fields` changes synthetic hidden fields while holding the seat view fixed and asserts ObservationV1 is unchanged.
- `test_observation_keeps_crforge_raw_scaled_values_for_audit` preserves raw public elixir counts alongside normalized values.
- `test_cycle_is_uncertain_before_four_public_card_plays` and related tests ensure the opponent's hand is not inferred before the public play ledger supports it.

These are converter and inference tests. They do not prove that every CRForge entity visibility rule is correct or that every v1 match mechanic is faithfully simulated.

## Remaining native acceptance checks

1. Run both seats through the actual pinned CRForge build and verify the seat-frame transform for every exposed entity and placement coordinate.
2. Compare `enemy_elixir` with CRForge's `EnemyElixirCountTest` under the exact v1 deck, including start, regeneration, ordinary card costs, command refusals and terminal ticks.
3. Verify that no champion, refund-producing card, or unsupported mechanic is enabled by the actual config/data.
4. Mutate one seat's hidden hand/queue/elixir while preserving the other seat's seat-visible state in a controlled engine test, and verify the receiving ObservationV1 is unchanged.
5. Inspect entity overflow and visibility edge cases, including tunnelling, unrevealed plays, projectiles and area effects.

Do not mark the native FAIR audit complete based only on Python converter tests.
