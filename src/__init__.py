"""The Missing List - a school-level dropout risk register for South Africa.

Every module lives under one of six packages, arranged by the stage of work it
belongs to. Where a file sits tells you what it does:

    common/     shared foundations - paths, identifiers, loading
    fetch/      stage 1 - pull raw data from public sources
    build/      stage 2 - turn raw files into clean tables
    eda/        stage 3 - profile and measure what the data contains
    features/   stage 3 - the rules and judgement calls that clean it
    model/      stage 4 - target, training, evaluation

Two rules hold the whole thing together.

Nothing here imports from app/. The Streamlit app is a window onto this code,
never the other way round. Every number the app displays is produced by a
function in this package, so the app and the trained model cannot disagree
about what the data says - which is exactly what happens when analysis logic
ends up living inside a dashboard.

Everything runs headless. The full pipeline works with the app never launched.
If reproducing a result required opening a browser, it would not be
reproducible.
"""
