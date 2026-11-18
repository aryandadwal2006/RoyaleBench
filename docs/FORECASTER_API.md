# Forecast model adapter API

RoyaleBench does not prescribe a model architecture or training framework. The forecasting evaluator accepts a Python object implementing this small protocol:

```python
class Forecaster:
    name: str

    def predict(
        self,
        observation: dict,
        actions: list[dict],
        *,
        horizon_ticks: int,
    ) -> dict:
        ...
```

- `observation` is the source ObservationV1 at the beginning of the forecast.
- `actions` contains the ActionV1 actions executed from that observation through the requested forecast horizon, in chronological order.
- `horizon_ticks` is the elapsed CRForge tick count from the source observation to the target observation. One engine tick is 50 ms.
- The return value is a predicted ObservationV1 payload. It is not compared to the actual target until after the predictor call returns.

The evaluator never passes match outcome labels, target observations or later future observations to `predict`. It passes deep copies of the source observation and actions, so a predictor cannot modify the dataset records used by subsequent calls.

## Minimal adapter

Load your model once in the constructor, then implement `predict`. The example below deliberately leaves model loading and inference as application-specific functions:

```python
from pathlib import Path
from typing import Any

from royalebench.forecasting import evaluate_forecaster, write_forecast_report


class ResearchForecaster:
    name = "my-world-model-checkpoint-2026-11-18"

    def __init__(self, checkpoint: str | Path):
        self.model = load_checkpoint(checkpoint)

    def predict(
        self,
        observation: dict[str, Any],
        actions: list[dict[str, Any]],
        *,
        horizon_ticks: int,
    ) -> dict[str, Any]:
        prediction = self.model.predict(
            observation=observation,
            actions=actions,
            horizon_ticks=horizon_ticks,
        )
        return decode_observation_v1(prediction)


forecaster = ResearchForecaster("checkpoints/model.pt")
report = evaluate_forecaster(
    "results/dataset/test.jsonl.gz",
    forecaster,
    horizons=(1, 2, 4),
)
write_forecast_report(report, "results/my-world-model-test.json")
```

Replace `load_checkpoint` and `decode_observation_v1` with the model-specific loader and decoder. The model must return a complete predicted observation structure; fields it does not predict can be copied from its source state only if the model deliberately defines that persistence assumption.

## Identity and metric semantics

CRForge uses stable, seat-local entity IDs assigned in order of first sight. An ID remains attached to the same visible entity during that entity's lifetime and is not shared between seats. Forecast metrics compare IDs only within the same match and seat trajectory.

Per horizon, the evaluator reports:

| Metric | Meaning |
|---|---|
| `tower_hp_mae` | Mean absolute error over the six visible towers' HP values |
| `elixir_mae` | Mean absolute error for own elixir and the public opponent-elixir estimate |
| `entity_type_precision/recall/f1` | Multiset match of visible entities by row name or entity kind |
| `entity_identity_precision/recall/f1` | Set match of non-negative stable entity IDs |
| `entity_position_mae_tiles` | Mean Euclidean position error for IDs present in both prediction and target, in seat-frame tiles |
| `entity_hp_mae` | Mean absolute HP error for matched entities whose HP is visible in both prediction and target |
| `entity_count_absolute_error` | Absolute difference in the total predicted and actual entity-type counts |

Unknown entity HP uses CRForge's sentinel value -1 and is excluded from the HP error. New entities absent from the source observation are evaluated through identity recall and entity-count/type metrics. Position and HP errors are calculated only for matched IDs with values present in both observations.

These measurements evaluate state prediction, not strategic usefulness by themselves. A model-based playing agent must separately implement the competitive Agent interface and enter a strategic tournament. Forecasting reports never contribute to Glicko-2 ratings.

## Data integrity requirements

Before prediction, the evaluator:
- verifies the compressed split's SHA-256 against the adjacent dataset manifest;
- recomputes every source and target observation hash;
- requires contiguous decision IDs for each match/seat;
- checks match ID and seat identity inside both observations;
- checks the recorded engine tick agrees with the next observation;
- checks adjacent transitions form one continuous observation-hash chain.

A missing decision or broken chain is a hard evaluation error. The evaluator does not silently skip gaps or join disjoint trajectory fragments.
