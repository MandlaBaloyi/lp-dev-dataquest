"""Stage 4 - target, training, evaluation.

Planned contents:

    label.py      defines the outcome being predicted
    train.py      fits the scorecard and its benchmark
    evaluate.py   metrics, calibration, feature importance

Currently empty. Everything here depends on matric results existing as a
table, and that extraction is the one piece still outstanding - without it
there is no outcome to train against.

Three commitments hold once this is built, all set out in
docs/dataquest_plan.txt:

The train/test split is by year, never at random. A school appears in up to
nineteen rows, so a random split would train and test on the same school and
score well by recognising it rather than by learning anything that transfers.

The primary model is a scorecard. Its output directs public spending, and a
score that cannot be explained cannot be defended by whoever has to act on it.
A gradient-boosted benchmark runs alongside it purely to measure what
interpretability costs.

No feature may use information from the year it predicts.
"""
