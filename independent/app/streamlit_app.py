"""The Missing List — a school-level learner-loss early warning system.

Run from the repository root:

    python -m streamlit run independent/app/streamlit_app.py

Needs the pipeline outputs (independent/outputs, independent/data). If they
are missing, run the four pipeline stages listed in independent/README.md.
"""
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from independent.src.paths import MODEL_FRAME, out  # noqa: E402

st.set_page_config(page_title="The Missing List", page_icon=":material/school:",
                   layout="wide")

missing = [p for p in (out("model.json"), out("ranking_2025.csv"), MODEL_FRAME) if not Path(p).exists()]
if missing:
    st.error("The pipeline outputs are missing. From the repository root run:\n\n"
             "```\npython -m independent.src.clean\npython -m independent.src.features\n"
             "python -m independent.src.train\npython -m independent.src.charts\n```")
    st.stop()

if "emis" not in st.session_state:
    st.session_state.emis = None

page = st.navigation([
    st.Page("app_pages/overview.py", title="Overview", icon=":material/home:", default=True),
    # The audit comes before the ranking deliberately. It is the challenge's own
    # question - find the discrepancies - and it is also the reason anything
    # downstream can be trusted.
    st.Page("app_pages/data_audit.py", title="Data audit", icon=":material/rule:"),
    st.Page("app_pages/risk_list.py", title="Risk list", icon=":material/format_list_numbered:"),
    st.Page("app_pages/school.py", title="School profile", icon=":material/school:"),
    st.Page("app_pages/simulator.py", title="Score simulator", icon=":material/tune:"),
    st.Page("app_pages/final_model.py", title="The final model", icon=":material/analytics:"),
    st.Page("app_pages/method.py", title="How we built it", icon=":material/science:"),
    st.Page("app_pages/security.py", title="Security", icon=":material/shield:"),
    st.Page("app_pages/business.py", title="Business model", icon=":material/payments:"),
], position="top")

page.run()

st.caption("The Missing List · DataQuest hackathon · Data: DBE EMIS masterlists 2007–2025 and NSC "
           "School Performance Reports 2008–2024, both open. School-level only; no learner records.")
