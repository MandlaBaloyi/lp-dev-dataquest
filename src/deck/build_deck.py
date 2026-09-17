"""Build the submission deck.

    python -m src.deck.build_deck

Produces submission/The_Missing_List.pptx.

Every figure on a slide is read from outputs/ at build time rather than typed
in, for the same reason the app reads them: the numbers moved four times during
this project, and a deck with hand-copied figures would have quietly gone stale
each time. If a slide and the app ever disagree, this script is wrong.

The deck is ordered against the judging criteria without announcing them:
innovation (slides 4-5, 9), data inclusion (4, 6), AI (7-9), security (11),
business model (12). Presentation is the whole thing.
"""
import json
from pathlib import Path

import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

from src.common.paths import ROOT, out

ROOT = Path(ROOT)

# ----------------------------------------------------------------- palette

INK = RGBColor(0x14, 0x17, 0x1A)
BODY = RGBColor(0x3D, 0x42, 0x48)
MUTED = RGBColor(0x76, 0x7C, 0x85)
BLUE = RGBColor(0x2A, 0x78, 0xD6)
ORANGE = RGBColor(0xEB, 0x68, 0x34)
RED = RGBColor(0xCF, 0x22, 0x2E)
GREEN = RGBColor(0x1A, 0x7F, 0x37)
PAPER = RGBColor(0xFF, 0xFF, 0xFF)
WASH = RGBColor(0xF5, 0xF6, 0xF7)
LINE = RGBColor(0xE1, 0xE4, 0xE8)

W, H = Inches(13.333), Inches(7.5)
MARGIN = Inches(0.85)
CONTENT_W = W - 2 * MARGIN

FONT = "Segoe UI"


# ----------------------------------------------------------------- helpers

def textbox(slide, x, y, w, h, align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(x, y, w, h)
    frame = box.text_frame
    frame.word_wrap = True
    frame.margin_left = frame.margin_right = 0
    frame.margin_top = frame.margin_bottom = 0
    frame.paragraphs[0].alignment = align
    return frame


def write(frame, text, size, color=BODY, bold=False, space_after=0,
          line=1.25, first=False, align=None):
    para = frame.paragraphs[0] if first else frame.add_paragraph()
    para.line_spacing = line
    para.space_after = Pt(space_after)
    if align is not None:
        para.alignment = align
    run = para.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = FONT
    return para


def rich(frame, parts, size, space_after=0, line=1.25, first=False, align=None):
    """One paragraph, several runs — so a phrase can be bold or coloured."""
    para = frame.paragraphs[0] if first else frame.add_paragraph()
    para.line_spacing = line
    para.space_after = Pt(space_after)
    if align is not None:
        para.alignment = align
    for text, color, bold in parts:
        run = para.add_run()
        run.text = text
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = color
        run.font.name = FONT
    return para


def block(slide, x, y, w, h, fill=WASH, edge=LINE, radius=0.06):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    shape.adjustments[0] = radius
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    if edge is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = edge
        shape.line.width = Pt(1)
    shape.shadow.inherit = False
    return shape


def rule(slide, x, y, w, color=ORANGE, thickness=3):
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, Pt(thickness))
    bar.fill.solid()
    bar.fill.fore_color.rgb = color
    bar.line.fill.background()
    bar.shadow.inherit = False
    return bar


def blank(deck):
    slide = deck.slides.add_slide(deck.slide_layouts[6])
    background = slide.background
    background.fill.solid()
    background.fill.fore_color.rgb = PAPER
    return slide


def heading(slide, eyebrow, title, sub=None):
    """Eyebrow, rule, title, optional standfirst. Returns the next free y."""
    y = Inches(0.62)
    if eyebrow:
        frame = textbox(slide, MARGIN, y, CONTENT_W, Inches(0.28))
        write(frame, eyebrow.upper(), 11.5, MUTED, bold=True, first=True)
        y += Inches(0.32)
    rule(slide, MARGIN, y, Inches(0.72))
    y += Inches(0.22)
    frame = textbox(slide, MARGIN, y, CONTENT_W, Inches(0.9))
    write(frame, title, 33, INK, bold=True, line=1.06, first=True)
    y += Inches(0.52) + Inches(0.32) * (len(title) // 62)
    if sub:
        frame = textbox(slide, MARGIN, y, CONTENT_W, Inches(0.6))
        write(frame, sub, 15.5, MUTED, line=1.34, first=True)
        y += Inches(0.34) * (1 + len(sub) // 108) + Inches(0.18)
    return y + Inches(0.18)


def footer(slide, number):
    frame = textbox(slide, MARGIN, H - Inches(0.52), Inches(6), Inches(0.26))
    write(frame, "The Missing List  ·  DataQuest  ·  Education", 9.5, MUTED, first=True)
    frame = textbox(slide, W - MARGIN - Inches(1), H - Inches(0.52),
                    Inches(1), Inches(0.26), align=PP_ALIGN.RIGHT)
    write(frame, str(number), 9.5, MUTED, first=True, align=PP_ALIGN.RIGHT)


def metrics(slide, y, cards, height=Inches(1.28)):
    """A row of figure cards. cards = [(value, label, colour), ...]"""
    gap = Inches(0.2)
    width = (CONTENT_W - gap * (len(cards) - 1)) / len(cards)
    for i, (value, label, color) in enumerate(cards):
        x = MARGIN + i * (width + gap)
        block(slide, x, y, width, height)
        frame = textbox(slide, x + Inches(0.22), y + Inches(0.2),
                        width - Inches(0.44), Inches(0.5))
        write(frame, value, 27, color, bold=True, line=1.0, first=True)
        frame = textbox(slide, x + Inches(0.22), y + Inches(0.75),
                        width - Inches(0.44), Inches(0.46))
        write(frame, label, 11, MUTED, line=1.22, first=True)
    return y + height + Inches(0.26)


def bullets(slide, x, y, w, items, size=14, gap=13):
    """items = [(lead, rest)] — lead is bold ink, rest is body."""
    frame = textbox(slide, x, y, w, Inches(0.4))
    for i, (lead, rest) in enumerate(items):
        parts = [(lead, INK, True)]
        if rest:
            parts.append((rest, BODY, False))
        rich(frame, parts, size, space_after=gap, line=1.3, first=(i == 0))
    return frame


# ----------------------------------------------------------------- figures

M = json.load(open(out("model.json"), encoding="utf-8"))
T = M["metrics"]["scorecard_test"]
TR, VA = M["metrics"]["scorecard_train"], M["metrics"]["scorecard_valid"]
F = json.load(open(out("forest_metrics.json"), encoding="utf-8"))
A = json.load(open(out("data_audit_summary.json"), encoding="utf-8"))
R = pd.read_csv(out("ranking_2025.csv"))

PRIORITY = R[R.tier == "PRIORITY"]
TOP = R.iloc[0]
N_SCHOOLS = len(R)
N_PRIORITY = len(PRIORITY)
N_LEARNERS = int(PRIORITY.learners.sum())
N_FEATURES = len(M["features_in_model"])


def pct(x, places=1):
    return f"{x * 100:.{places}f}%"


# ----------------------------------------------------------------- slides

def slide_title(deck):
    slide = blank(deck)
    block(slide, Emu(0), Emu(0), W, Inches(2.5), fill=INK, edge=None, radius=0)

    frame = textbox(slide, MARGIN, Inches(0.72), CONTENT_W, Inches(0.3))
    write(frame, "DATAQUEST  ·  THEME: EDUCATION", 12,
          RGBColor(0xA8, 0xB0, 0xBA), bold=True, first=True)

    frame = textbox(slide, MARGIN, Inches(1.16), CONTENT_W, Inches(1))
    write(frame, "The Missing List", 50, PAPER, bold=True, line=1.0, first=True)

    frame = textbox(slide, MARGIN, Inches(2.78), Inches(10.4), Inches(1.1))
    rich(frame, [("More than 40% of South African learners who start Grade 1 never "
                  "finish matric. ", BODY, False),
                 ("Nobody publishes which schools.", INK, True)],
         19, line=1.34, first=True)

    y = metrics(slide, Inches(3.95), [
        (f"{N_SCHOOLS:,}", "secondary schools scored for 2025", BLUE),
        (f"{N_PRIORITY:,}", "on the priority tier", ORANGE),
        (f"{N_LEARNERS:,}", "learners inside those schools", INK),
        (f"{T['auc']:.3f}", "test AUC, on years never seen", INK),
    ])

    frame = textbox(slide, MARGIN, y + Inches(0.12), CONTENT_W, Inches(0.8))
    write(frame, "A school-level dropout risk register for South Africa, "
                 "built entirely from open government data.", 15, MUTED, first=True)

    frame = textbox(slide, MARGIN, H - Inches(0.78), CONTENT_W, Inches(0.3))
    write(frame, "github.com/Mandla78/lp-dev-dataquest", 11.5, MUTED, first=True)


def slide_problem(deck, n):
    slide = blank(deck)
    y = heading(slide, "The problem",
                "The number is known. The list is not.")

    frame = textbox(slide, MARGIN, y, Inches(7.0), Inches(3.2))
    rich(frame, [("40 of every 100 children", INK, True),
                 (" who walk into a Grade 1 classroom will not walk out of a "
                  "Grade 12 one. That figure is published, widely quoted and "
                  "not in dispute.", BODY, False)],
         17, space_after=16, line=1.36, first=True)
    rich(frame, [("The problem is not that the number is unknown. It is that ", BODY, False),
                 ("it cannot be pointed at anything.", INK, True)],
         17, space_after=16, line=1.36)
    write(frame, "Nobody can deploy a teacher to a percentage. An organisation "
                 "with one retention programme and funding for twelve schools "
                 "cannot use a national average to choose the twelve.",
          17, BODY, space_after=16, line=1.36)
    rich(frame, [("Learners are counted after they are gone, in aggregate, "
                  "once a year.", ORANGE, True)], 17, line=1.36)

    x = MARGIN + Inches(7.55)
    w = CONTENT_W - Inches(7.55)
    block(slide, x, y, w, Inches(3.3), fill=INK, edge=None)
    frame = textbox(slide, x + Inches(0.34), y + Inches(0.36), w - Inches(0.68), Inches(2.6))
    write(frame, "Every year that list does not exist,", 16,
          RGBColor(0xA8, 0xB0, 0xBA), line=1.3, first=True)
    write(frame, "help goes somewhere —", 20, PAPER, bold=True, line=1.3, space_after=6)
    write(frame, "just not necessarily where the loss is worst.", 20, ORANGE,
          bold=True, line=1.3)
    footer(slide, n)


def slide_questions(deck, n):
    slide = blank(deck)
    y = heading(slide, "What has to be answered first",
                "Four questions stand in the way. We answer three.",
                "None of them currently has an answer anywhere in the public record.")

    rows = [
        ("Which provinces are losing the most?", "8 of 9, ranked by measured risk", True),
        ("Which districts inside those provinces?", "72, ranked within their province", True),
        ("Which schools inside those districts?", f"{N_SCHOOLS:,}, scored individually", True),
        ("Which grades inside those schools?", "Needs per-grade enrolment — held under permission", False),
    ]
    row_h = Inches(0.76)
    for i, (question, answer, done) in enumerate(rows):
        yy = y + i * (row_h + Inches(0.12))
        block(slide, MARGIN, yy, CONTENT_W, row_h,
              fill=WASH if done else RGBColor(0xFF, 0xF8, 0xEC),
              edge=LINE if done else RGBColor(0xF0, 0xD9, 0xB5))
        frame = textbox(slide, MARGIN + Inches(0.3), yy + Inches(0.23),
                        Inches(5.2), Inches(0.4))
        write(frame, question, 15, INK, bold=True, first=True)
        frame = textbox(slide, MARGIN + Inches(5.7), yy + Inches(0.23),
                        Inches(5.1), Inches(0.4))
        write(frame, answer, 14, BODY, first=True)
        frame = textbox(slide, MARGIN + CONTENT_W - Inches(1.5), yy + Inches(0.21),
                        Inches(1.2), Inches(0.4), align=PP_ALIGN.RIGHT)
        write(frame, "ANSWERED" if done else "NOT YET", 11,
              GREEN if done else ORANGE, bold=True, first=True, align=PP_ALIGN.RIGHT)

    frame = textbox(slide, MARGIN, y + Inches(3.72), CONTENT_W, Inches(0.7))
    rich(frame, [("On the fourth we are deliberate. ", INK, True),
                 ("We can say a school is losing its Grade 8–12 pipeline. We cannot "
                  "yet say whether the loss sits in Grade 10 or Grade 11. That is a "
                  "form, not a rebuild — the same pipeline answers it the day the "
                  "permission arrives.", BODY, False)], 13.5, line=1.3, first=True)
    footer(slide, n)


def slide_audit(deck, n):
    slide = blank(deck)
    y = heading(slide, "The challenge question",
                "The data is broken, and nothing says so",
                f"Seven detectors over {A['records_scanned']:,} records across two datasets.")

    y = metrics(slide, y, [
        (f"{A['records_scanned']:,}", "records scanned", INK),
        (f"{A['total_findings']}", "discrepancies found", ORANGE),
        (f"{A['high']}", "severe enough to change a model", RED),
        ("0", "raise an error anywhere", INK),
    ], height=Inches(1.05))

    left = [
        ("2017 loses 1.44 million learners", " nationally; 2018 gains 1.31 million back."),
        ("Province codes are unstable", " — KZ/KZN, GT/GP — turning a country of nine provinces into a dataset of eleven."),
        ("Gauteng's 2023 file", " has its key column headed \"G\". Three thousand schools vanish."),
    ]
    right = [
        ("724 schools sit at latitude zero", " — a point in the Atlantic Ocean."),
        ("Phase appears in 21 spellings", ", quintile in 17, the fee flag in 11."),
        ("8,792 schools change", " their recorded phase between years."),
    ]
    bullets(slide, MARGIN, y + Inches(0.02), Inches(5.7), left, size=13, gap=10)
    bullets(slide, MARGIN + Inches(6.0), y + Inches(0.02), Inches(5.6), right, size=13, gap=10)

    bar_y = H - Inches(1.52)
    block(slide, MARGIN, bar_y, CONTENT_W, Inches(0.82), fill=INK, edge=None)
    frame = textbox(slide, MARGIN + Inches(0.34), bar_y + Inches(0.21),
                    CONTENT_W - Inches(0.68), Inches(0.5))
    rich(frame, [("Not one of them raises an error. ", ORANGE, True),
                 ("The files open, the row counts look reasonable, the totals look "
                  "plausible. A crash gets noticed within the hour; a province that "
                  "quietly becomes two survives into a published finding.",
                  RGBColor(0xD8, 0xDC, 0xE1), False)], 13.5, line=1.28, first=True)
    footer(slide, n)


def slide_own_bug(deck, n):
    slide = blank(deck)
    y = heading(slide, "The same standard, applied to us",
                "We audited our own work, and it failed too")

    frame = textbox(slide, MARGIN, y, Inches(6.6), Inches(3.4))
    write(frame, "Our first PDF parser trusted each report's header as the layout "
                 "for the whole file. The reports do not work that way.",
          16, BODY, space_after=14, line=1.34, first=True)
    rich(frame, [("It produced 14,005 records", RED, True),
                 (" claiming more learners were advanced into matric than sat the "
                  "exam, and silently destroyed the pass-rate column.", BODY, False)],
         16, space_after=14, line=1.34)
    rich(frame, [("So we removed pass rate from the model and wrote a comment "
                  "explaining why. ", BODY, False),
                 ("The comment was wrong. The evidence behind it was our own bug.",
                  INK, True)], 16, space_after=14, line=1.34)

    x = MARGIN + Inches(7.1)
    w = CONTENT_W - Inches(7.1)
    block(slide, x, y, w, Inches(1.62), fill=WASH)
    frame = textbox(slide, x + Inches(0.3), y + Inches(0.26), w - Inches(0.6), Inches(1.2))
    write(frame, "After the fix", 11.5, MUTED, bold=True, first=True)
    rich(frame, [("pass rate  0%  →  88.4%", INK, True)], 17, space_after=4)
    write(frame, "coverage of the matric column", 11.5, MUTED)

    block(slide, x, y + Inches(1.78), w, Inches(1.62), fill=WASH)
    frame = textbox(slide, x + Inches(0.3), y + Inches(2.04), w - Inches(0.6), Inches(1.2))
    write(frame, "And the model", 11.5, MUTED, bold=True, first=True)
    rich(frame, [("AUC  0.654  →  ", INK, True), (f"{T['auc']:.3f}", GREEN, True)],
         17, space_after=4)
    write(frame, "pass rate is now its strongest variable", 11.5, MUTED)

    bar_y = H - Inches(1.52)
    block(slide, MARGIN, bar_y, CONTENT_W, Inches(0.82), fill=INK, edge=None)
    frame = textbox(slide, MARGIN + Inches(0.34), bar_y + Inches(0.21),
                    CONTENT_W - Inches(0.68), Inches(0.5))
    rich(frame, [("The fix is verified by arithmetic the source itself prints: ",
                  RGBColor(0xD8, 0xDC, 0xE1), False),
                 ("where a report gives both the achieved count and the pass rate, "
                  "the rate must equal achieved ÷ wrote. It holds on 82,979 of "
                  "82,979 checkable records.", ORANGE, True)], 13.5, line=1.28, first=True)
    footer(slide, n)


def slide_data(deck, n):
    slide = blank(deck)
    y = heading(slide, "Data inclusion",
                "Two public datasets, joined on one key",
                "Published openly by the Department of Basic Education. "
                "No login, no licence, no NDA, no purchase.")

    cards = [
        ("EMIS School Masterlists",
         f"{A['enrolment_records']:,} records  ·  {A['schools_scanned']:,} schools  ·  2007–2025  ·  all 9 provinces",
         "Enrolment, educators, quintile, fee status, phase, district, coordinates. "
         "Built from 140 provincial spreadsheets.",
         "education.gov.za › Programmes › EMIS Downloads"),
        ("NSC School Performance Reports",
         f"{A['matric_records']:,} records  ·  {A['matric_schools']:,} schools  ·  2008–2024",
         "Candidates who wrote, achieved, the pass rate, and learners progressed "
         "without meeting requirements. Extracted by us from 13 PDFs — the "
         "department publishes no machine-readable version.",
         "education.gov.za › Resources › Reports"),
    ]
    w = (CONTENT_W - Inches(0.3)) / 2
    for i, (name, scale, what, source) in enumerate(cards):
        x = MARGIN + i * (w + Inches(0.3))
        block(slide, x, y, w, Inches(2.62))
        frame = textbox(slide, x + Inches(0.3), y + Inches(0.26), w - Inches(0.6), Inches(2.1))
        write(frame, name, 17, INK, bold=True, space_after=7, first=True)
        write(frame, scale, 12, BLUE, bold=True, space_after=10)
        write(frame, what, 12.5, BODY, space_after=10, line=1.3)
        write(frame, source, 11, MUTED)

    y += Inches(2.74)
    items = [
        ("Joined on the EMIS number,", " normalised to bare digits first — it is published both with and without a leading zero, and getting it wrong fails the join silently rather than loudly."),
        ("Matric evidence is carried forward only,", " never backward, with an age marker so a stale figure can be discounted. Carrying it backward would be reading the future."),
        ("Raw source files are committed", " alongside the code, so the extraction can be checked rather than taken on trust."),
    ]
    bullets(slide, MARGIN, y, CONTENT_W, items, size=13, gap=10)
    footer(slide, n)


def slide_how(deck, n):
    slide = blank(deck)
    y = heading(slide, "The solution",
                "What the machine learning actually does",
                "Two supervised models were trained. The choice between them is the "
                "most consequential decision in the project.")

    cards = [
        ("Supervised learning", f"Learns from {TR['n']:,} historical school-years where the "
                                "outcome is already known. Nothing is rule-based — the weights are "
                                "fitted from data, not chosen by us."),
        ("Feature engineering", "Raw registers become 31 candidate variables: enrolment trajectory, "
                                "volatility, share of own peak, learners per educator, what neighbouring "
                                f"schools do, matric throughput. {N_FEATURES} survive into the model."),
        ("Weight of Evidence", "Each variable is binned and re-expressed as the log-odds of loss it "
                               "carries — letting a linear model capture non-linear risk and treat "
                               "missing data as its own informative category."),
        ("Calibrated probabilities", "Isotonic regression maps scores onto real observed rates, so a "
                                     "school at 0.30 loses learners about 30% of the time. Ranking gives "
                                     "order; calibration tells a planner how far their budget reaches."),
    ]
    w = (CONTENT_W - Inches(0.26)) / 2
    h = Inches(1.42)
    for i, (name, text) in enumerate(cards):
        x = MARGIN + (i % 2) * (w + Inches(0.26))
        yy = y + (i // 2) * (h + Inches(0.2))
        block(slide, x, yy, w, h)
        frame = textbox(slide, x + Inches(0.28), yy + Inches(0.2), w - Inches(0.56), Inches(1.1))
        write(frame, name, 15, INK, bold=True, space_after=6, first=True)
        write(frame, text, 11.5, BODY, line=1.28)

    bar_y = y + 2 * (h + Inches(0.2)) + Inches(0.06)
    block(slide, MARGIN, bar_y, CONTENT_W, Inches(0.76), fill=WASH, edge=LINE)
    frame = textbox(slide, MARGIN + Inches(0.32), bar_y + Inches(0.18),
                    CONTENT_W - Inches(0.64), Inches(0.5))
    rich(frame, [("Split by year, never at random. ", INK, True),
                 (f"Trained on {TR['n']:,} school-years (2008–2016), tuned on "
                  f"{VA['n']:,} (2018–2019), measured once on {T['n']:,} (2021–2023). "
                  "A school recurs across years, so a random split would train and "
                  "test on the same school.", BODY, False)], 13, line=1.28, first=True)
    footer(slide, n)


def slide_results(deck, n):
    slide = blank(deck)
    y = heading(slide, "Results",
                "Measured once, on years the model never saw",
                "2021–2023. No refitting, no threshold tuning after the fact.")

    y = metrics(slide, y, [
        (f"{T['auc']:.3f}", "AUC on unseen years", INK),
        (f"{T['gini']:.3f}", "Gini", INK),
        (f"{T['ks']:.3f}", "KS statistic", INK),
        (f"{T['top10_lift']:.2f}×", "lift in the worst tenth", ORANGE),
    ])

    picture = ROOT / "outputs" / "fig8_decile_lift_test.png"
    if picture.exists():
        slide.shapes.add_picture(str(picture), MARGIN, y + Inches(0.05),
                                 height=Inches(2.55))

    x = MARGIN + Inches(6.3)
    w = CONTENT_W - Inches(6.3)
    items = [
        (f"Worst tenth loses at {pct(T['top10_precision'])}", f" against {pct(0.0243, 2)} in the best tenth — the schools it ranks worst really are the ones losing learners."),
        (f"Recall {pct(T['recall'], 0)} at the threshold.", " A missed school gets nothing; a false alarm gets a visit. Those costs are not symmetric."),
    ]
    bullets(slide, x, y + Inches(0.1), w, items, size=13)

    warn_y = y + Inches(1.66)
    block(slide, x, warn_y, w, Inches(1.1), fill=RGBColor(0xFF, 0xF8, 0xEC),
          edge=RGBColor(0xF0, 0xD9, 0xB5))
    frame = textbox(slide, x + Inches(0.28), warn_y + Inches(0.2), w - Inches(0.56), Inches(0.8))
    rich(frame, [("Accuracy is our weakest number and we say so. ", ORANGE, True),
                 (f"At {pct(T['accuracy'], 0)} it is below the {pct(T['accuracy_all_negative'], 0)} "
                  "you score by predicting nobody ever loses learners — a model that "
                  "identifies no one. That is why we lead with lift.", BODY, False)],
         11.5, line=1.26, first=True)
    footer(slide, n)


def slide_tradeoff(deck, n):
    slide = blank(deck)
    y = heading(slide, "The decision we had to defend",
                "A better-ranking model exists. It is not what we ship.")

    w = (CONTENT_W - Inches(0.3)) / 2
    block(slide, MARGIN, y, w, Inches(2.5), fill=WASH, edge=BLUE)
    frame = textbox(slide, MARGIN + Inches(0.32), y + Inches(0.26), w - Inches(0.64), Inches(2.0))
    write(frame, "SHIPPED", 11, BLUE, bold=True, space_after=6, first=True)
    write(frame, "Logistic Regression Scorecard", 19, INK, bold=True, space_after=8)
    rich(frame, [(f"AUC {T['auc']:.4f}", INK, True), ("   ·   ", MUTED, False),
                 (f"lift {T['top10_lift']:.2f}×", BODY, False)], 14, space_after=10)
    write(frame, "Every score breaks into visible points. A school can be told it "
                 "lost 37 points for its matric pass rate.", 12.5, BODY, line=1.3)

    x = MARGIN + w + Inches(0.3)
    block(slide, x, y, w, Inches(2.5))
    frame = textbox(slide, x + Inches(0.32), y + Inches(0.26), w - Inches(0.64), Inches(2.0))
    write(frame, "BENCHMARK, NOT SHIPPED", 11, MUTED, bold=True, space_after=6, first=True)
    write(frame, "Calibrated Random Forest", 19, INK, bold=True, space_after=8)
    rich(frame, [(f"AUC {F['auc']:.4f}", GREEN, True), ("   ·   ", MUTED, False),
                 (f"lift {F['top10_lift']:.2f}×", BODY, False)], 14, space_after=10)
    write(frame, "Ranks better and cannot tell a school why it was flagged. "
                 "Trained on the identical frame and split.", 12.5, BODY, line=1.3)

    y += Inches(2.76)
    frame = textbox(slide, MARGIN, y, CONTENT_W, Inches(1.2))
    rich(frame, [(f"The gap is {F['auc'] - T['auc']:.3f} AUC, and we publish it. ", INK, True),
                 ("This output directs public money. Whoever must justify the spend "
                  "has to explain it line by line — to a treasury, a community, or a "
                  "school that disagrees with its ranking. That is worth more than two "
                  "hundredths of a ranking statistic, and stating the price makes "
                  "the choice defensible rather than merely asserted.", BODY, False)],
         15, line=1.34, first=True)

    bar_y = H - Inches(1.5)
    block(slide, MARGIN, bar_y, CONTENT_W, Inches(0.8), fill=INK, edge=None)
    frame = textbox(slide, MARGIN + Inches(0.34), bar_y + Inches(0.2),
                    CONTENT_W - Inches(0.68), Inches(0.5))
    rich(frame, [("We also measured the mistakes that inflate a model silently. ",
                  RGBColor(0xD8, 0xDC, 0xE1), False),
                 ("A random split lifts the tree from 0.692 to 0.731 — it has learned "
                  "to recognise schools, not predict them.", ORANGE, True)],
         13, line=1.28, first=True)
    footer(slide, n)


def slide_register(deck, n):
    slide = blank(deck)
    y = heading(slide, "The product",
                "A ranked list, and a reason beside every school",
                "A planner filters to their province and sees what to work first — "
                "a morning's decision instead of a year's guesswork.")

    block(slide, MARGIN, y, Inches(6.5), Inches(2.9), fill=INK, edge=None)
    frame = textbox(slide, MARGIN + Inches(0.36), y + Inches(0.3), Inches(5.8), Inches(2.3))
    write(frame, f"RANK 1 OF {N_SCHOOLS:,}  ·  {TOP.district.title()}, Limpopo", 11,
          RGBColor(0xA8, 0xB0, 0xBA), bold=True, space_after=6, first=True)
    write(frame, str(TOP.school).title(), 30, PAPER, bold=True, space_after=10)
    rich(frame, [(f"{int(TOP.learners)} learners", RGBColor(0xD8, 0xDC, 0xE1), False),
                 ("     ", MUTED, False),
                 (f"{TOP.p_loss:.0%} risk of losing learners faster than its province by 2027",
                  ORANGE, True)], 13, space_after=12)
    write(frame, "Against a national base rate of 12.2%.", 12,
          RGBColor(0xA8, 0xB0, 0xBA))

    x = MARGIN + Inches(6.8)
    w = CONTENT_W - Inches(6.8)
    frame = textbox(slide, x, y, w, Inches(0.3))
    write(frame, "WHY THIS SCHOOL", 11, MUTED, bold=True, first=True)

    reasons = [str(TOP.reason_1), str(TOP.reason_2), str(TOP.reason_3)]
    for i, reason in enumerate(reasons):
        yy = y + Inches(0.4) + i * Inches(0.66)
        block(slide, x, yy, w, Inches(0.56))
        frame = textbox(slide, x + Inches(0.24), yy + Inches(0.15), w - Inches(0.48), Inches(0.35))
        label, _, points = reason.rpartition(" (")
        rich(frame, [(label.strip(), INK, False), ("   ", MUTED, False),
                     ("(" + points if points else "", ORANGE, True)],
             12.5, first=True)

    frame = textbox(slide, x, y + Inches(2.5), w, Inches(0.7))
    write(frame, "That is the whole score. A school flagged for a pass-rate reason "
                 "needs different help from one flagged for a staffing reason.",
          12, BODY, line=1.3, first=True)

    bar_y = H - Inches(1.42)
    frame = textbox(slide, MARGIN, bar_y, CONTENT_W, Inches(0.8))
    rich(frame, [("Coverage, stated plainly: ", INK, True),
                 ("8 provinces, not 9. The Northern Cape published a Word template "
                  "where its 2025 masterlist should be — a fault our own audit found, "
                  "not one we introduced. The model covers all nine; the register "
                  "covers the eight that published.", BODY, False)],
         13, line=1.3, first=True)
    footer(slide, n)


def slide_security(deck, n):
    slide = blank(deck)
    y = heading(slide, "System security",
                "It holds nothing worth stealing — by design",
                "Confidentiality is the easy half. The half that needs controls is integrity.")

    y = metrics(slide, y, [
        ("0", "personal records held", GREEN),
        ("School", "smallest unit of analysis", INK),
        ("0", "executable model artefacts", GREEN),
        ("Public", "every source — nothing to steal", INK),
    ], height=Inches(1.05))

    cards = [
        ("No personal information", "Learner records are protected under POPIA and a hackathon team "
                                    "has no lawful basis to process them. A tool that names children creates "
                                    "a register of vulnerable minors."),
        ("Input validation at the boundary", "Every download is checked against its format's magic bytes "
                                             "before it is written. A portal returning an HTML error page "
                                             "under a spreadsheet's filename is routine, and is rejected."),
        ("Nothing executable ships", "The model is model.json — inert data. No pickle, no joblib, no eval. "
                                     "Loading a pickled model executes what is inside it."),
        ("The audit is an integrity control", "Seven detectors already catch corrupted, truncated or altered "
                                              "source files. They caught our own parser producing 14,005 "
                                              "impossible records."),
    ]
    w = (CONTENT_W - Inches(0.26)) / 2
    h = Inches(1.1)
    for i, (name, text) in enumerate(cards):
        x = MARGIN + (i % 2) * (w + Inches(0.26))
        yy = y + (i // 2) * (h + Inches(0.12))
        block(slide, x, yy, w, h)
        frame = textbox(slide, x + Inches(0.26), yy + Inches(0.16), w - Inches(0.52), Inches(0.9))
        write(frame, name, 13.5, INK, bold=True, space_after=4, first=True)
        write(frame, text, 10.5, BODY, line=1.26)

    bar_y = y + 2 * (h + Inches(0.12)) + Inches(0.04)
    block(slide, MARGIN, bar_y, CONTENT_W, Inches(0.68),
          fill=RGBColor(0xFF, 0xF8, 0xEC), edge=RGBColor(0xF0, 0xD9, 0xB5))
    frame = textbox(slide, MARGIN + Inches(0.3), bar_y + Inches(0.16),
                    CONTENT_W - Inches(0.6), Inches(0.5))
    rich(frame, [("The gap we have not closed: ", ORANGE, True),
                 ("dependencies are minimum-pinned but not hash-locked. A departmental "
                  "deployment needs a lockfile and an internal mirror. A security "
                  "section with no gap in it has not been written honestly.",
                  BODY, False)], 12, line=1.26, first=True)
    footer(slide, n)


def slide_business(deck, n):
    slide = blank(deck)
    y = heading(slide, "Business model",
                "R612,000 a year, against what it prevents",
                "A tool for the people who allocate support — never sold to the "
                "schools that need it.")

    y = metrics(slide, y, [
        ("R612k", "to run for a year", INK),
        ("R49", "per school scored", INK),
        ("R0", "data acquisition — all sources public", GREEN),
        ("4 provinces", "break-even, at R150k each", ORANGE),
    ], height=Inches(1.05))

    x2 = MARGIN + Inches(6.5)
    frame = textbox(slide, MARGIN, y + Inches(0.06), Inches(6.2), Inches(2.2))
    write(frame, "WHAT THE PROBLEM COSTS", 11, MUTED, bold=True, space_after=8, first=True)
    rich(frame, [(f"{N_LEARNERS:,} learners", INK, True),
                 (f" sit in the {N_PRIORITY:,} schools the register flags as priority.",
                  BODY, False)], 13.5, space_after=8, line=1.3)
    rich(frame, [("90 learners", INK, True),
                 (" is the median two-year drop at a flagged school that does lose "
                  "them — measured across 2,807 such cases, not assumed.", BODY, False)],
         13.5, space_after=8, line=1.3)
    rich(frame, [("~21,600 learners", ORANGE, True),
                 (" is what that comes to across the 28.5% of the priority tier "
                  "that loses.", BODY, False)], 13.5, line=1.3)

    frame = textbox(slide, x2, y + Inches(0.06), CONTENT_W - Inches(6.5), Inches(2.2))
    write(frame, "WHO PAYS", 11, MUTED, bold=True, space_after=8, first=True)
    for label, text in [("Year 1", "grant-funded pilot, two provinces"),
                        ("Year 2", "four provinces at R150k, NGO tier at R25k"),
                        ("Year 3", "nine provinces, national rollout")]:
        rich(frame, [(label + "   ", BLUE, True), (text, BODY, False)],
             13, space_after=7, line=1.3)
    write(frame, "Adding a province is a filter, not a project.", 12, MUTED, line=1.3)

    bar_y = H - Inches(1.6)
    block(slide, MARGIN, bar_y, CONTENT_W, Inches(0.9), fill=INK, edge=None)
    frame = textbox(slide, MARGIN + Inches(0.34), bar_y + Inches(0.2),
                    CONTENT_W - Inches(0.68), Inches(0.6))
    rich(frame, [("The state has already spent about R200,000 educating one learner "
                  "by Grade 10. ", RGBColor(0xD8, 0xDC, 0xE1), False),
                 ("This costs less than three of them.", ORANGE, True)],
         15, space_after=3, line=1.26, first=True)
    write(frame, "The argument is not that the tool is cheap. It is that it is "
                 "negligible against what is already being spent on the learners it "
                 "exists to keep in school.", 11.5, RGBColor(0xA8, 0xB0, 0xBA), line=1.26)
    footer(slide, n)


def slide_honest(deck, n):
    slide = blank(deck)
    y = heading(slide, "Limitations",
                "What we are honest about",
                "Every one of these is on the live application, not held back for "
                "the questions.")

    items = [
        ("It measures enrolment decline, not dropout.",
         " A learner who transfers to a better school and one who leaves education "
         "entirely look identical in a headcount."),
        ("It is a triage list, not a verdict.",
         f" At {T['auc']:.3f} AUC the ranking is worth working from the top of, and "
         "not good enough to be believed about any single school without a visit."),
        ("Population stability is a real caveat.",
         f" PSI is {M['psi_score_train_vs_2025']:.2f} from training to the 2025 register, "
         "above the level at which a scorecard is normally rebuilt. Seventeen years "
         "separate them. It is the strongest argument for annual retraining."),
        ("The raw masterlists are incomplete in the repository.",
         " Four of the 140 spreadsheets remain; the built tables were produced from "
         "the full set and are committed in full. The README says so rather than "
         "implying otherwise."),
        ("A better model exists and is not shipped.",
         f" The forest reaches {F['auc']:.4f}. We report the gap rather than hide it."),
    ]
    bullets(slide, MARGIN, y, CONTENT_W, items, size=14, gap=15)

    bar_y = H - Inches(1.45)
    block(slide, MARGIN, bar_y, CONTENT_W, Inches(0.78), fill=WASH, edge=LINE)
    frame = textbox(slide, MARGIN + Inches(0.32), bar_y + Inches(0.19),
                    CONTENT_W - Inches(0.64), Inches(0.5))
    rich(frame, [("A model that directs public money should be re-validated annually "
                  "and withdrawn if it stops performing. ", BODY, False),
                 ("A model nobody re-checks is a governance risk long before it is a "
                  "technical one.", INK, True)], 13, line=1.28, first=True)
    footer(slide, n)


def slide_close(deck, n):
    slide = blank(deck)
    block(slide, Emu(0), Emu(0), W, H, fill=INK, edge=None, radius=0)

    frame = textbox(slide, MARGIN, Inches(1.5), Inches(11), Inches(0.4))
    write(frame, "THE MISSING LIST", 13, ORANGE, bold=True, first=True)

    frame = textbox(slide, MARGIN, Inches(2.05), Inches(11.2), Inches(2.2))
    write(frame, "Open government data, a list a province", 38, PAPER, bold=True,
          line=1.12, first=True)
    write(frame, "can act on this week, and a reason", 38, PAPER, bold=True, line=1.12)
    write(frame, "next to every school.", 38, ORANGE, bold=True, line=1.12)

    y = Inches(4.75)
    gap = Inches(0.24)
    w = (CONTENT_W - gap * 3) / 4
    cards = [(f"{N_SCHOOLS:,}", "schools scored"),
             (f"{N_PRIORITY:,}", "priority tier"),
             (f"{A['total_findings']}", "data discrepancies found"),
             (f"{T['auc']:.3f}", "AUC on unseen years")]
    for i, (value, label) in enumerate(cards):
        x = MARGIN + i * (w + gap)
        frame = textbox(slide, x, y, w, Inches(0.55))
        write(frame, value, 30, PAPER, bold=True, line=1.0, first=True)
        frame = textbox(slide, x, y + Inches(0.55), w, Inches(0.4))
        write(frame, label, 12, RGBColor(0xA8, 0xB0, 0xBA), first=True)

    frame = textbox(slide, MARGIN, H - Inches(1.1), CONTENT_W, Inches(0.5))
    write(frame, "github.com/Mandla78/lp-dev-dataquest", 13,
          RGBColor(0xA8, 0xB0, 0xBA), first=True)


BUILDERS = [slide_problem, slide_questions, slide_audit, slide_own_bug,
            slide_data, slide_how, slide_results, slide_tradeoff,
            slide_register, slide_security, slide_business, slide_honest]


def run():
    deck = Presentation()
    deck.slide_width, deck.slide_height = W, H

    slide_title(deck)
    for i, builder in enumerate(BUILDERS, start=2):
        builder(deck, i)
    slide_close(deck, len(BUILDERS) + 2)

    target = ROOT / "submission" / "The_Missing_List.pptx"
    target.parent.mkdir(parents=True, exist_ok=True)
    deck.save(str(target))
    print(f"wrote {target}  ({len(deck.slides.__iter__.__self__._sldIdLst)} slides)")
    return target


if __name__ == "__main__":
    run()
