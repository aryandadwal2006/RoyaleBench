# RoyaleBench v1 trajectory dataset

RoyaleBench generates its trajectory corpus from offline CRForge matches. No user-supplied replay set, manual annotation or training run is required.

## Match records

Every agent decision produces one seat-perspective transition:
- ObservationV1 at decision time.
- The agent's ActionV1 response.
- The next seat-perspective ObservationV1 after the engine advances.
- Match ID, seed, seat, decision ID and engine tick.
- SHA-256 hashes of both observation payloads.
- Match outcome and engine provenance.

The same match contributes transitions from both seats. Train/validation/test assignment is performed at the complete-match level, so a battle never contributes to more than one split.

## Output files

A dataset export writes train.jsonl.gz, validation.jsonl.gz, test.jsonl.gz and dataset_manifest.json.

The manifest records match IDs by split, transition counts, deterministic split seed, engine metadata and SHA-256 of each compressed shard.

## Split policy

Simulator seed groups are deterministically ordered by SHA-256 of the split seed and simulator seed. Every match using the same simulator seed, including paired seat swaps and other agent pairings, stays in the same partition. Default proportions are 80/10/10, adjusted to keep all three partitions non-empty when there are at least three completed matches. For small pilots, a split is not statistically representative; use a larger frozen corpus for reported results.

Only completed matches with a valid win/draw result are exported. Engine-fault, truncated, protocol-failure and other void matches are excluded.

## Reproducibility

Do not edit a generated shard after export. Re-run the exporter with the same source match directories and split seed to reproduce the same match assignment and data content. Dataset manifests preserve the exact source match IDs and engine metadata.

## Forecasting evaluation

The trajectory data supports action-conditioned state forecasting. A forecast-only model is evaluated separately from competitive agent ratings. A model-based playing agent must also implement the competitive Agent interface.

The versioned ForecastRequestV1 and ForecastResponseV1 JSON Schemas define the forecast exchange contract. A request binds an observation, the intervening action sequence and the requested horizon to the source observation hash. The evaluator currently includes a persistence baseline and reports tower-HP MAE, elixir MAE, entity-type precision/recall/F1 and entity-count error at multiple decision-interval horizons. It is a baseline evaluation path, not yet a learned-model leaderboard.

A training, validation and test split is only a data-management prerequisite. The final held-out evaluation should use a separately frozen match corpus or hidden seeds and should not be used for policy tuning.


## Run the forecasting baseline

After building the dataset, evaluate the persistence baseline on the held-out test shard:

```powershell
python -m royalebench forecast-eval --split results/dataset/test.jsonl.gz --horizons 1,2,4 --output results/forecast-persistence.json
```

The predictor receives only the starting ObservationV1 and the actions in the forecast interval. It does not receive match outcomes, target observations or future observations. The report records the input contract and the number of evaluated examples at each horizon. The persistence baseline is a sanity reference, not a learned world model.
