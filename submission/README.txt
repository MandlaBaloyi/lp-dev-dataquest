SUBMISSION MATERIALS
The Missing List · DataQuest · Theme: Education
=========================================================

What goes in this folder: the presentation deck, the written submission
documents, and anything else handed to a judge rather than run as code.

CURRENT CONTENTS
  The_Missing_List.pptx        the deck, 14 slides
  The_Missing_List.pdf         the same deck as PDF, for a machine without
                               PowerPoint or a projector that will not connect
  Project_Specification.docx   problem, solution, data, variables
  Merge_Report.docx            why two tracks were run and what each found

THE DECK IS BUILT BY A SCRIPT, NOT EDITED BY HAND

    python -m src.deck.build_deck

  Every figure on every slide is read from outputs/ at build time. The numbers
  in this project moved four times - after the leakage fix, the threshold fix,
  the PDF extraction fix and the matric carry-forward - and a deck with
  hand-typed figures would have quietly gone stale at each one.

  So if a slide and the app ever disagree, the script is wrong and should be
  fixed there. Editing the .pptx directly works, but the next build overwrites
  it.

  Slide order, against the judging criteria:
    1  title           7  what the ML does        (AI)
    2  the problem     8  results                 (AI)
    3  four questions  9  the trade-off we defend (innovation)
    4  the audit       10 the register in use
       (innovation, data inclusion)
    5  our own bug     11 security                (system security)
       (innovation)    12 business model          (business model)
    6  the sources     13 limitations
       (data inclusion) 14 close

STILL TO DO
  recapture docs/screenshots/ - the five there predate the app restructure and
  do not cover data audit, the final model, security or business model

WHERE THE NUMBERS COME FROM
  Every figure quoted in a slide should be traceable to one of these:

    outputs/model.json          model metrics on unseen years
    outputs/forest_metrics.json the benchmark that is not shipped
    outputs/data_audit.csv      the 19 audit findings
    outputs/ranking_2025.csv    the register itself
    outputs/fig1-8*.png         figures already rendered
    docs/screenshots/           app screenshots, as a demo fallback

  If a number is not in one of those, it should not be on a slide.
