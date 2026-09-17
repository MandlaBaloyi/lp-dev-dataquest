"""Stage 3 - measuring what the data actually contains.

    quality.py   missing, dirty and impossible values
    woe.py       weight of evidence and information value

quality.py keeps three kinds of problem apart because they fail differently.
Missing is honest - a blank cell announces itself. Impossible is findable once
you think to look: a latitude of zero is a valid number and a point in the
Atlantic Ocean. Dirty is the dangerous one, because nothing looks wrong at
all - a column holding both "3" and "Q3" is complete by every summary measure,
and splits one category into two the moment a model reads it.

woe.py scores how much each variable predicts, so variables can be ranked
before any model is fitted. Its fit and transform steps are deliberately
separate: bins must be learned from training data and then applied unchanged
to test data. Fitting them across everything lets every bin see the test set,
which inflates every metric downstream without raising anything.
"""
