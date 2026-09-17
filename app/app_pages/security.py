"""Security and privacy position.

The strongest security claim this system can make is that it holds nothing
worth stealing. That is a design decision rather than a consequence, and this
page sets out what was given up to make it true.
"""
import streamlit as st

st.title("Security and privacy")
st.markdown(
    "The safest personal data is the personal data you never collect. This system "
    "holds **no learner records, no names, no identity numbers and no household "
    "information** — not because they are well protected, but because they were "
    "never taken in."
)

with st.container(horizontal=True):
    st.metric("Personal records held", "0", "by design, not by policy",
              delta_color="off", delta_arrow="off", border=True)
    st.metric("Smallest unit of analysis", "School", "never a learner",
              delta_color="off", delta_arrow="off", border=True)
    st.metric("Data sources", "Public", "no login, no licence, no NDA",
              delta_color="off", delta_arrow="off", border=True)
    st.metric("POPIA exposure", "None", "no personal information processed",
              delta_color="off", delta_arrow="off", border=True)

st.divider()
st.subheader("What we deliberately gave up")

st.warning(
    "**We could have built a more accurate model.** Learner-level records would "
    "identify which individual children are at risk, and would almost certainly "
    "predict better than school-level aggregates. We did not pursue them.\n\n"
    "Those records are protected under POPIA, and a hackathon team has no lawful "
    "basis to process them. A tool that names children also creates a register of "
    "vulnerable minors — and that register becomes a liability the moment it "
    "exists, regardless of how carefully it is held.\n\n"
    "So the system was scoped to answer *which schools need support* rather than "
    "*which children are failing*. It is the weaker question and the right one."
)

st.divider()
st.subheader("The controls")

controls = [
    (":material/person_off:", "No personal information",
     "Every record describes a school: enrolment counts, staffing counts, funding "
     "band, location, matric candidate totals. No field identifies a person, so "
     "there is no personal information to breach, leak or subpoena."),
    (":material/public:", "Public sources only",
     "All inputs are published openly by the Department of Basic Education and "
     "Statistics South Africa. No credential is used to obtain them, so no "
     "credential can be stolen from us, and no access agreement can be violated."),
    (":material/history:", "Reproducible and auditable",
     "Every dataset is rebuilt from source by version-controlled scripts. Any "
     "figure in this application can be traced back to the published file it came "
     "from, which means a disputed result can be checked rather than argued about."),
    (":material/visibility:", "No black box",
     "The scorecard's weights are published in full. A school can see exactly why "
     "it was ranked where it was — which is both a fairness property and a "
     "security one, because an opaque score invites the suspicion that it was "
     "tampered with."),
    (":material/gpp_maybe:", "Aggregation as protection",
     "Because the smallest unit is a school of hundreds of learners, no output can "
     "be reverse-engineered to an individual. Small schools below a minimum "
     "enrolment are excluded, which also removes the cases where aggregate figures "
     "start to describe identifiable people."),
    (":material/lock_reset:", "Least privilege on deployment",
     "The application is read-only over pre-computed outputs. It holds no database "
     "credentials, accepts no uploads and writes nothing back, so the running "
     "service has no privileges worth escalating."),
]

for row in range(0, len(controls), 2):
    columns = st.columns(2)
    for column, (icon, name, text) in zip(columns, controls[row:row + 2]):
        with column.container(border=True, height="stretch"):
            st.markdown(f":{icon.strip(':')}: **{name}**")
            st.caption(text)

st.divider()
st.subheader("If this were deployed in a department")

st.markdown(
    "The current build is a read-only analysis tool. Putting it inside a "
    "provincial department would add three things, and they are worth stating "
    "because they are where the real risk would sit:"
)
st.markdown(
    "- **Authentication and role separation.** A district official should see "
    "their own district; a provincial planner should see the province. Not a "
    "confidentiality control, since the data is public, but an accountability one "
    "— it records who acted on which school.\n"
    "- **An audit log of decisions, not data.** The sensitive artefact in "
    "deployment is not the enrolment figures; it is the record of which schools "
    "were flagged and what was done about them. That log would need retention "
    "rules and access control of its own.\n"
    "- **A published model card and a review cycle.** A score that directs public "
    "money should be re-validated annually and withdrawn if it stops performing. "
    "A model nobody re-checks is a governance risk long before it is a technical "
    "one."
)

st.divider()
st.subheader("The honest risk")

st.error(
    "**Misuse is the real exposure, and it is not a technical one.** A ranked list "
    "of schools can be read as a league table and used to punish the schools at "
    "the top rather than support them. That would invert the entire purpose.\n\n"
    "The mitigation is presentation, not encryption: the output is framed as a "
    "support-allocation list, every score carries the reasons behind it, and the "
    "model's accuracy is stated plainly so nobody mistakes a triage signal for a "
    "verdict on a school."
)
