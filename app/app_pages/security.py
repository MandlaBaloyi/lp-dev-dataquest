"""Security and privacy position.

The strongest security claim this system can make is that it holds nothing
worth stealing. That is a design decision rather than a consequence, and this
page sets out what was given up to make it true.

Confidentiality is the easy half and it is close to free here, because there is
no personal data. The half that actually needs controls is integrity: every
input is downloaded over the internet from a government site, and the output
directs public money.
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
    st.metric("Executable model artefacts", "0", "JSON, never a pickle",
              delta_color="off", delta_arrow="off", border=True)

st.divider()
st.subheader("What we deliberately gave up")

st.warning(
    """**We could have built a more accurate model.** Learner-level records would
identify which individual children are at risk, and would almost certainly predict
better than school-level aggregates. We did not pursue them.

Those records are protected under POPIA, and a hackathon team has no lawful basis to
process them. A tool that names children also creates a register of vulnerable minors
— and that register becomes a liability the moment it exists, regardless of how
carefully it is held.

So the system was scoped to answer *which schools need support* rather than *which
children are failing*. It is the weaker question and the right one."""
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
    (":material/verified_user:", "Input validation at the boundary",
     "Every download is checked against its format's magic bytes before it is "
     "written to disk — an .xlsx must begin with a ZIP header, a PDF with %PDF. "
     "A government portal returning an HTML error page under a spreadsheet's "
     "filename is a routine event, and it is rejected here rather than parsed into "
     "silent nonsense downstream."),
    (":material/code_off:", "Nothing executable in the artefacts",
     "The trained model ships as model.json and scorecard.csv — inert data, read "
     "with a JSON parser. There is no pickle, no joblib file and no eval anywhere "
     "in the codebase. Loading a pickled model executes whatever is inside it, so "
     "the usual way to ship a model is also the usual way to ship code execution. "
     "A scorecard does not need to be a program, so it is not one."),
    (":material/history:", "Reproducible and auditable",
     "Every dataset is rebuilt from source by version-controlled scripts. Any "
     "figure in this application can be traced back to the published file it came "
     "from, which means a disputed result can be checked rather than argued about."),
    (":material/rule:", "Continuous integrity checking",
     "Seven detectors run over 572,607 records and return 19 findings. They were "
     "built to audit the department's data, but they are equally an integrity "
     "control on our own: a corrupted, truncated or altered source file changes "
     "totals, breaks identifier continuity or produces impossible values, and all "
     "three are things the scan already looks for."),
    (":material/visibility:", "No black box",
     "The scorecard's weights are published in full. A school can see exactly why "
     "it was ranked where it was — which is both a fairness property and a "
     "security one, because an opaque score invites the suspicion that it was "
     "tampered with."),
    (":material/lock_reset:", "Least privilege on deployment",
     "The application is read-only over pre-computed outputs. It holds no database "
     "credentials, accepts no uploads and writes nothing back, so the running "
     "service has no privileges worth escalating."),
]

for row in range(0, len(controls), 2):
    columns = st.columns(2)
    for column, (icon, name, text) in zip(columns, controls[row:row + 2]):
        with column.container(border=True, height="stretch"):
            st.markdown(f"{icon} **{name}**")
            st.caption(text)

st.divider()
st.subheader("What we are actually defending against")

st.markdown(
    "Listing controls without naming a threat proves nothing. These are the five "
    "ways this system could realistically go wrong, and what stands in the way of "
    "each — including the one where the honest answer is *not enough yet*."
)

threats = [
    ("A source file is corrupted, truncated or replaced upstream",
     "**Covered.** Magic bytes are checked on download; the audit then scans for "
     "collapsing totals, broken identifier continuity and impossible values. This "
     "is not hypothetical — the same scan caught **our own** PDF parser producing "
     "14,005 impossible records, which is the strongest evidence available that it "
     "works on data nobody expected to be wrong.",
     True),
    ("Someone edits the register to move a school up or down the list",
     "**Covered.** Every output is regenerable from public sources by committed "
     "scripts, so an altered ranking is caught by rebuilding it and comparing. "
     "Tampering is not prevented so much as made pointless, because the truth stays "
     "independently recoverable by anyone who wants to check.",
     True),
    ("A malicious model artefact is substituted",
     "**Covered by construction.** The artefact is JSON with no execution path. The "
     "worst a substituted file can do is produce wrong scores, which the row above "
     "catches. It cannot run code on the machine that loads it.",
     True),
    ("Learner personal data leaks",
     "**Not applicable.** None is held at any stage, including in the raw downloads. "
     "There is no incident available to have.",
     True),
    ("A compromised dependency",
     "**Partially covered, and this is the real gap.** Dependencies are declared and "
     "minimum-pinned in requirements.txt, but they are not pinned to exact versions "
     "and not hash-locked. A deployment inside a department would need a lockfile "
     "and a vetted internal mirror. We are naming this rather than leaving it off "
     "the list.",
     False),
]

for threat, response, covered in threats:
    with st.container(border=True):
        icon = ":material/check_circle:" if covered else ":material/warning:"
        st.markdown(f"{icon} **{threat}**")
        st.caption(response)

st.divider()
st.subheader("If this were deployed in a department")

st.markdown(
    "The current build is a read-only analysis tool. Putting it inside a "
    "provincial department would add four things, and they are worth stating "
    "because they are where the real risk would sit:"
)
st.markdown(
    """- **Authentication and role separation.** A district official should see their
own district; a provincial planner should see the province. Not a confidentiality
control, since the data is public, but an accountability one — it records who acted
on which school.
- **An audit log of decisions, not data.** The sensitive artefact in deployment is not
the enrolment figures; it is the record of which schools were flagged and what was
done about them. That log would need retention rules and access control of its own.
- **A dependency lockfile and an internal mirror.** The gap named above, closed.
- **A published model card and a review cycle.** A score that directs public money
should be re-validated annually and withdrawn if it stops performing. A model nobody
re-checks is a governance risk long before it is a technical one."""
)

st.divider()
st.subheader("The honest risk")

st.error(
    """**Misuse is the real exposure, and it is not a technical one.** A ranked list of
schools can be read as a league table and used to punish the schools at the top rather
than support them. That would invert the entire purpose.

The mitigation is presentation, not encryption: the output is framed as a
support-allocation list, every score carries the reasons behind it, and the model's
accuracy is stated plainly so nobody mistakes a triage signal for a verdict on a
school."""
)
