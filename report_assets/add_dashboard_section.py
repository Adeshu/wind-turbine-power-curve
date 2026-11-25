import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt

import build_report as br

ROOT = Path(r"C:\Users\Ashish\Desktop\SML")
DOCX = ROOT / "SML_Project_Report.docx"
FIG = ROOT / "report_assets" / "figures"

HEADING = "5.7 Interactive Dashboard"
INTRO = (
    "The six-tab Streamlit dashboard makes the complete workflow interactive. "
    "The sidebar exposes the dataset, the physical knots, the outlier rules, the "
    "MAD threshold, the number of folds, the random seed, and the model list, so "
    "every result in this chapter can be reproduced from the interface. The "
    "screenshots below show each tab as rendered by the dashboard."
)

FIGURES = [
    ("dash_01_overview.png", "Fig 5.8: Overview tab \u2014 dataset summary, data-quality checks, and distributions"),
    ("dash_02_cleaning.png", "Fig 5.9: Cleaning & outliers tab \u2014 rule-wise counts and before/after scatter"),
    ("dash_03_power_curve.png", "Fig 5.10: Power curve tab \u2014 fitted B-spline with cut-in and rated knots"),
    ("dash_04_model_comparison.png", "Fig 5.11: Model comparison tab \u2014 cross-validated metrics and fold-level RMSE"),
    ("dash_05_diagnostics.png", "Fig 5.12: Diagnostics tab \u2014 out-of-fold residual and distribution plots"),
    ("dash_06_methodology.png", "Fig 5.13: Methodology tab \u2014 method summary and Module 4 mapping"),
]


def set_para(p, *, align=WD_ALIGN_PARAGRAPH.JUSTIFY, before=0, after=0, line=1.5, keep_next=False):
    pf = p.paragraph_format
    pf.alignment = align
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    pf.keep_with_next = keep_next
    return p


def main():
    doc = Document(str(DOCX))
    for p in doc.paragraphs:
        if p.text.strip().startswith(HEADING):
            raise SystemExit("Dashboard section already present; nothing to do.")

    discussion = None
    limitations = None
    for p in doc.paragraphs:
        text = p.text.strip()
        if re.match(r"^5\.\d+\s+Discussion$", text):
            discussion = p
        if re.match(r"^5\.\d+\s+Limitations$", text):
            limitations = p

    if discussion is None:
        raise SystemExit("Could not find the Discussion heading in Chapter 5.")
    if limitations is None:
        raise SystemExit("Could not find the Limitations heading in Chapter 5.")

    # Renumber before inserting so the numbering stays unique.
    for run in limitations.runs:
        run.text = run.text.replace("5.8 Limitations", "5.9 Limitations")
    for run in discussion.runs:
        run.text = run.text.replace("5.7 Discussion", "5.8 Discussion")

    target = discussion
    heading = target.insert_paragraph_before()
    set_para(heading, align=WD_ALIGN_PARAGRAPH.LEFT, before=12, after=6, keep_next=True)
    run = heading.add_run(HEADING)
    br.set_run_font(run, size=16, bold=True)

    intro = target.insert_paragraph_before()
    set_para(intro, after=6)
    br.set_run_font(intro.add_run(INTRO), size=12)

    for filename, caption in FIGURES:
        image_path = FIG / filename
        if not image_path.exists():
            raise SystemExit(f"Missing screenshot: {image_path}")

        pic_para = target.insert_paragraph_before()
        set_para(pic_para, align=WD_ALIGN_PARAGRAPH.CENTER, before=6, after=2, keep_next=True)
        pic_para.add_run().add_picture(str(image_path), width=Inches(6.4))

        cap_para = target.insert_paragraph_before()
        set_para(cap_para, align=WD_ALIGN_PARAGRAPH.CENTER, before=2, after=10, line=1.0)
        br.set_run_font(cap_para.add_run(caption), size=11, italic=True)

    doc.save(str(DOCX))
    print("inserted dashboard section into", DOCX)


if __name__ == "__main__":
    main()
