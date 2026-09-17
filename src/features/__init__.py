"""Stage 3 - the rules that turn raw records into modelling inputs.

    clean.py       normalisation rules
    decisions.py   the judgement calls, stored as configuration

The split between these two files is the important part.

clean.py holds rules with a correct answer. "Q3" and "3" are the same funding
band; merging them is simply right, and there is nothing to debate. Those are
code, and they are unit tested.

decisions.py holds choices where a reasonable person could go either way, and
where the choice changes the result. Do special-needs schools belong in a study
of matric attrition? Is a school with no recorded funding band usable, or
dropped? Those are written to a configuration file, version controlled, and
read identically by the pipeline and the app - so the answer is recorded and
can be defended, rather than buried in a line of code nobody remembers writing.

One principle runs through both: unknown is preserved, never dropped. Records
with missing funding bands turn out to be systematically smaller schools, so
discarding them would remove a real category rather than remove noise.
"""
