"""The Missing List — a school-level learner-loss early warning system.

Run from the repository root:

    python -m streamlit run app/streamlit_app.py

Needs the built tables in datasets/processed and the artefacts in outputs.
If they are missing, run the pipeline stages listed in the project README.
"""
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.common.paths import MODEL_FRAME, out  # noqa: E402

st.set_page_config(page_title="The Missing List", page_icon=":material/school:",
                   layout="wide")

missing = [p for p in (out("model.json"), out("ranking_2025.csv"), MODEL_FRAME) if not Path(p).exists()]
if missing:
    st.error("The pipeline outputs are missing. From the repository root run:\n\n"
             "```\npython -m src.clean\npython -m src.features\n"
             "python -m src.train\npython -m src.charts\n```")
    st.stop()

if "emis" not in st.session_state:
    st.session_state.emis = None

# Ordered as the work was done, because that is also the order the argument
# has to be made in: audit the data before claiming anything from it, explain
# the method before showing the model, show the model before showing what it
# ranks, and only then argue that it is safe to run and worth paying for.
#
# Kept flat rather than grouped into sections - the numbers carry the sequence,
# and a flat bar is what the top navigation renders cleanly.
page = st.navigation([
    st.Page("app_pages/overview.py", title="Overview",
            icon=":material/home:", default=True),

    # What is wrong with the data, before anything is claimed from it.
    st.Page("app_pages/data_audit.py", title="1 · Data audit",
            icon=":material/rule:"),
    st.Page("app_pages/method.py", title="2 · How we built it",
            icon=":material/science:"),

    # The model, and every number it should be judged on.
    st.Page("app_pages/final_model.py", title="3 · The final model",
            icon=":material/analytics:"),

    # What it produces: the ranking, one school, and a what-if.
    st.Page("app_pages/risk_list.py", title="4 · Risk list",
            icon=":material/format_list_numbered:"),
    st.Page("app_pages/school.py", title="5 · School profile",
            icon=":material/school:"),
    st.Page("app_pages/simulator.py", title="6 · Score simulator",
            icon=":material/tune:"),

    # Why it is safe to run, and how it pays for itself.
    st.Page("app_pages/security.py", title="7 · Security",
            icon=":material/shield:"),
    st.Page("app_pages/business.py", title="8 · Business model",
            icon=":material/payments:"),
], position="top")

page.run()

st.caption("The Missing List · DataQuest hackathon · Data: DBE EMIS masterlists 2007–2025 and NSC "
           "School Performance Reports 2008–2024, both open. School-level only; no learner records.")
