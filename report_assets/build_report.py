from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor

ROOT = Path(r"C:\Users\Ashish\Desktop\SML")
ASSETS = ROOT / "report_assets"
FIG = ASSETS / "figures"
OUT_DOCX = ROOT / "SML_Project_Report.docx"

BODY_W = Inches(6.85)
FONT = "Times New Roman"


# ----------------------------------------------------------------------------
# low level helpers
# ----------------------------------------------------------------------------
def set_run_font(run, size=12, bold=False, italic=False, color=None, name=FONT):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    if color is not None:
        run.font.color.rgb = RGBColor(*color)
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attr), name)


def para(
    doc,
    text="",
    size=12,
    bold=False,
    italic=False,
    align=WD_ALIGN_PARAGRAPH.JUSTIFY,
    before=0,
    after=0,
    line=1.5,
    style=None,
    left=None,
    first=None,
    keep_next=False,
    color=None,
):
    p = doc.add_paragraph(style=style)
    pf = p.paragraph_format
    pf.alignment = align
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    if left is not None:
        pf.left_indent = Inches(left)
    if first is not None:
        pf.first_line_indent = Inches(first)
    pf.keep_with_next = keep_next
    if text:
        run = p.add_run(text)
        set_run_font(run, size=size, bold=bold, italic=italic, color=color)
    return p


def bullet(doc, text, size=12, line=1.5):
    p = doc.add_paragraph(style="List Bullet")
    pf = p.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.line_spacing = line
    pf.left_indent = Inches(0.5)
    pf.first_line_indent = Inches(-0.25)
    run = p.add_run(text)
    set_run_font(run, size=size)
    return p


def numbered(doc, number, text, size=12, line=1.5):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf.space_before = Pt(0)
    pf.space_after = Pt(0)
    pf.line_spacing = line
    pf.left_indent = Inches(0.4)
    pf.first_line_indent = Inches(-0.4)
    run = p.add_run(f"{number}. ")
    set_run_font(run, size=size, bold=True)
    run2 = p.add_run(text)
    set_run_font(run2, size=size)
    return p


def page_break(doc):
    p = doc.add_paragraph()
    p.add_run().add_break(WD_BREAK.PAGE)
    return p


def heading(doc, text, size=16, align=WD_ALIGN_PARAGRAPH.LEFT, before=0, after=6, line=1.5):
    return para(
        doc,
        text,
        size=size,
        bold=True,
        align=align,
        before=before,
        after=after,
        line=line,
        keep_next=True,
    )


def chapter(doc, number, title, bookmark, bid, new_page=True):
    p = para(
        doc,
        f"CHAPTER {number}",
        size=18,
        bold=True,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        before=0,
        after=0,
        line=1.5,
        keep_next=True,
    )
    if new_page:
        p.paragraph_format.page_break_before = True
    t = para(
        doc,
        title,
        size=18,
        bold=True,
        align=WD_ALIGN_PARAGRAPH.LEFT,
        before=0,
        after=10,
        line=1.5,
        keep_next=True,
    )
    add_bookmark(t, bookmark, bid)
    return p


def add_bookmark(paragraph, name, bid):
    start = OxmlElement("w:bookmarkStart")
    start.set(qn("w:id"), str(bid))
    start.set(qn("w:name"), name)
    end = OxmlElement("w:bookmarkEnd")
    end.set(qn("w:id"), str(bid))
    paragraph._p.insert(0, start)
    paragraph._p.append(end)


def figure(doc, path, width, caption):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(str(path), width=Inches(width))
    cap = para(
        doc,
        caption,
        size=11,
        italic=True,
        align=WD_ALIGN_PARAGRAPH.CENTER,
        before=2,
        after=10,
        line=1.0,
    )
    return cap


def shade_cell(cell, fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    tcPr.append(shd)


def set_cell(cell, text, size=9, bold=False, align=WD_ALIGN_PARAGRAPH.LEFT):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = align
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(1)
    p.paragraph_format.line_spacing = 1.0
    run = p.add_run(str(text))
    set_run_font(run, size=size, bold=bold)


def repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    trPr.append(el)


def cant_split(row):
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:cantSplit")
    el.set(qn("w:val"), "true")
    trPr.append(el)


def set_col_widths(table, widths):
    table.autofit = False
    for row in table.rows:
        for idx, width in enumerate(widths):
            row.cells[idx].width = width


def keep_table_together(table):
    rows = table.rows
    for row in rows[:-1]:
        for cell in row.cells:
            for p in cell.paragraphs:
                p.paragraph_format.keep_with_next = True


def data_table(doc, headers, rows, widths, font_size=9, header_size=9):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    hdr = table.rows[0]
    for i, h in enumerate(headers):
        set_cell(hdr.cells[i], h, size=header_size, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
        shade_cell(hdr.cells[i], "DCE6F1")
    repeat_header(hdr)
    cant_split(hdr)
    for r in rows:
        cells = table.add_row().cells
        for i, value in enumerate(r):
            align = WD_ALIGN_PARAGRAPH.CENTER if i == 0 else WD_ALIGN_PARAGRAPH.LEFT
            set_cell(cells[i], value, size=font_size, align=align)
    set_col_widths(table, widths)
    keep_table_together(table)
    return table


def borderless_table(doc, rows, cols):
    table = doc.add_table(rows=rows, cols=cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    return table


def remove_table_borders(table):
    tblPr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "nil")
        borders.append(el)
    tblPr.append(borders)


def add_page_borders(section, val, sz):
    sectPr = section._sectPr
    pgBorders = OxmlElement("w:pgBorders")
    pgBorders.set(qn("w:offsetFrom"), "page")
    for edge in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), val)
        el.set(qn("w:sz"), str(sz))
        el.set(qn("w:space"), "24")
        el.set(qn("w:color"), "auto")
        pgBorders.append(el)
    sectPr.insert_element_before(
        pgBorders,
        "w:lnNumType",
        "w:pgNumType",
        "w:cols",
        "w:formProt",
        "w:vAlign",
        "w:noEndnote",
        "w:titlePg",
        "w:textDirection",
        "w:bidi",
        "w:rtlGutter",
        "w:docGrid",
        "w:printerSettings",
        "w:sectPrChange",
    )


def set_page_number_format(section, fmt, start):
    sectPr = section._sectPr
    pgNumType = sectPr.find(qn("w:pgNumType"))
    if pgNumType is None:
        pgNumType = OxmlElement("w:pgNumType")
        sectPr.insert_element_before(
            pgNumType,
            "w:cols",
            "w:formProt",
            "w:vAlign",
            "w:noEndnote",
            "w:titlePg",
            "w:textDirection",
            "w:bidi",
            "w:rtlGutter",
            "w:docGrid",
            "w:printerSettings",
            "w:sectPrChange",
        )
    pgNumType.set(qn("w:fmt"), fmt)
    pgNumType.set(qn("w:start"), str(start))


def add_page_field(paragraph):
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    txt = OxmlElement("w:t")
    txt.text = "1"
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_begin)
    run._r.append(instr)
    run._r.append(fld_sep)
    run._r.append(txt)
    run._r.append(fld_end)
    set_run_font(run, size=10)


def setup_section(section, cover=False):
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    if cover:
        section.top_margin = Cm(2.05)
        section.bottom_margin = Cm(1.59)
        section.left_margin = Cm(1.23)
        section.right_margin = Cm(1.16)
        add_page_borders(section, "single", 12)
    else:
        section.top_margin = Cm(1.27)
        section.bottom_margin = Cm(1.27)
        section.left_margin = Cm(1.75)
        section.right_margin = Cm(1.79)
        section.footer_distance = Inches(0.1)
        add_page_borders(section, "thinThickSmallGap", 18)


def add_body_footer(section):
    section.footer.is_linked_to_previous = False
    footer = section.footer
    p = footer.paragraphs[0]
    p.text = ""
    add_page_field(p)


# ----------------------------------------------------------------------------
# content
# ----------------------------------------------------------------------------
def cover(doc):
    para(doc, "VISVESVARAYA TECHNOLOGICAL UNIVERSITY", size=18, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=2)
    para(doc, "Jnana Sangama, Belgaum- 590 018, Karnataka", size=14,
         align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=8)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(2)
    p.add_run().add_picture(str(ASSETS / "vtu_logo.jpeg"), width=Inches(1.09))

    para(doc, "Statistical ML for DS (BAD702)", size=14, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=2)
    para(doc, "Project Report", size=14, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=2)
    para(doc, "on", size=14, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=4)
    para(doc, "", size=10, line=1.0, after=4)
    para(doc, "\u201cWIND TURBINE POWER CURVE MODELLING USING SPLINE REGRESSION\u201d",
         size=14, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=6,
         color=(0xFF, 0x00, 0x00))
    para(doc, "Submitted in partial fulfillment for the award of degree of", size=14,
         italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=3)
    para(doc, "BACHELOR OF ENGINEERING", size=14, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=1)
    para(doc, "IN", size=14, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=1)
    para(doc, "ARTIFICIAL INTELLIGENCE & DATA SCIENCE", size=14, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=1)
    para(doc, "For the Academic Year 2025-26", size=12,
         align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=6)
    para(doc, "", size=10, line=1.0, after=0)
    para(doc, "Submitted By", size=14, italic=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=2)
    para(doc, "ADESH U", size=13.5, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=0,
         color=(0xFF, 0x00, 0x00))
    para(doc, "[1DB23AD002]", size=13.5, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=6,
         color=(0xFF, 0x00, 0x00))
    para(doc, "", size=10, line=1.0, after=0)
    para(doc, "Under the Guidance of", size=13,
         align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=1)
    para(doc, "Dr. Gowramma G S", size=13, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=0)
    para(doc, "Professor & Head", size=13,
         align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=0)
    para(doc, "Dept. of AI & DS", size=13, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=0)
    para(doc, "(Artificial Intelligence & Data Science)", size=13, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=6)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(4)
    p.add_run().add_picture(str(ASSETS / "dbit_logo.jpeg"), width=Inches(0.92))

    para(doc, "Department Of AI & DS (Artificial Intelligence & Data Science)", size=16, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=0)
    para(doc, "DON BOSCO INSTITUTE OF TECHNOLOGY", size=16, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=0)
    para(doc, "(An Autonomous Institute affiliated to VTU, Belgavi)", size=13,
         bold=True, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=0)
    para(doc, "Mysore Road, Kumbalagodu, Bengaluru-560074", size=13,
         bold=True, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=0)
    para(doc, "2025-26", size=13, bold=True, italic=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=0)


def certificate(doc):
    para(doc, "", size=10, line=1.0, after=0)
    para(doc, "Don Bosco Institute of Technology", size=18, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=0,
         color=(0x99, 0x66, 0x33))
    para(doc, "Kumbalagodu Mysuru Road Bengaluru-560074", size=12, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=4)
    para(doc, "DEPARTMENT OF AI & DS (ARTIFICIAL INTELLIGENCE & DATA SCIENCE)", size=12,
         bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=8,
         color=(0x4F, 0x81, 0xBD))
    para(doc, "", size=10, line=1.0, after=0)

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(2)
    p.add_run().add_picture(str(ASSETS / "dbit_logo.jpeg"), width=Inches(0.96))

    h = para(doc, "CERTIFICATE", size=14, bold=True,
             align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=10)
    add_bookmark(h, "bm_certificate", 1)

    body = para(doc, "", size=12, align=WD_ALIGN_PARAGRAPH.JUSTIFY, line=1.5, after=24)
    set_run_font(
        body.add_run(
            "This is to certify that the Statistical Machine Learning project work on the topic "
        ),
        size=12,
    )
    set_run_font(
        body.add_run(
            "\u201cWIND TURBINE POWER CURVE MODELLING USING SPLINE REGRESSION\u201d"
        ),
        size=12,
        color=(0xFF, 0x00, 0x00),
    )
    set_run_font(
        body.add_run(
            " has been successfully presented at Don Bosco Institute of Technology by ADESH U "
            "(1DB23AD002) in partial fulfillment of the requirements for the VI Semester degree "
            "of Bachelor of Engineering in Artificial Intelligence & Data Science of "
            "Visvesvaraya Technological University, Belagavi during the academic year "
            "2025-2026. It is certified that all corrections and suggestions indicated for "
            "internal assessment have been incorporated in the project report deposited in the "
            "departmental library. The project report has been approved as it satisfies the "
            "academic requirements in respect of project work prescribed for the said degree."
        ),
        size=12,
    )

    para(doc, "", size=12, line=1.0, after=30)
    table = borderless_table(doc, 2, 3)
    remove_table_borders(table)
    headers = ["Signature of the Guide", "Signature of the HOD", "Signature of the Principal"]
    names = ["Dr. Gowramma G S", "Dr. Gowramma G S", "Dr. Naghabhushana B S"]
    details = [
        "Professor & Head\nDept. of AI & DS\nDBIT, Bengaluru",
        "Professor & Head\nDept. of AI & DS\nDBIT, Bengaluru",
        "Principal\nDBIT, Bengaluru",
    ]
    for i in range(3):
        set_cell(table.rows[0].cells[i], headers[i], size=11.5, bold=True,
                 align=WD_ALIGN_PARAGRAPH.CENTER)
        set_cell(table.rows[1].cells[i], names[i] + "\n" + details[i], size=11.5,
                 align=WD_ALIGN_PARAGRAPH.CENTER)
    set_col_widths(table, [Inches(2.28), Inches(2.28), Inches(2.28)])


def acknowledgement(doc):
    h = para(doc, "ACKNOWLEDGEMENT", size=18, bold=True,
             align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=14)
    h.paragraph_format.page_break_before = True
    add_bookmark(h, "bm_ack", 2)
    paragraphs = [
        "The satisfaction and euphoria that accompany the successful completion of any task "
        "would be incomplete without the mention of the people who made it possible, whose "
        "constant guidance and encouragement crowned the efforts with success.",
        "I would like to profoundly thank the Management of Don Bosco Institute of Technology "
        "for providing a healthy environment for the successful completion of this project work.",
        "I would like to express my thanks to Principal Dr. B. S. Nagabhushana, Don Bosco "
        "Institute of Technology, Bengaluru, for the encouragement that motivated me throughout "
        "this project.",
        "I would like to express my deepest sense of gratitude to my guide Dr. Gowramma G S, "
        "Professor and Head of the Department of Artificial Intelligence and Data Science, for "
        "her constant support, encouragement, and guidance throughout the project work.",
        "I also thank all teaching and non-teaching staff of the Department of Artificial "
        "Intelligence and Data Science who have helped directly and indirectly throughout the "
        "project work.",
    ]
    for text in paragraphs:
        para(doc, text, size=12, line=1.5, after=8)
    para(doc, "", size=12, line=1.0, after=0)
    para(doc, "Adesh U (1DB23AD002)", size=12, bold=True,
         align=WD_ALIGN_PARAGRAPH.RIGHT, line=1.0, after=0)


def abstract(doc):
    h = para(doc, "ABSTRACT", size=18, bold=True,
             align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=14)
    h.paragraph_format.page_break_before = True
    add_bookmark(h, "bm_abstract", 3)
    text = (
        "Wind turbine output does not increase linearly with wind speed. It remains close to "
        "zero below the cut-in speed, rises steeply through the ramp region, and flattens at "
        "rated power. A straight-line model therefore gives misleading forecasts to grid "
        "operators and hides periods of underperformance. This project develops a spline "
        "regression framework for modelling the power curve of a wind turbine using ten-minute "
        "SCADA observations from the T1.csv dataset. The dataset contains 50,530 records for "
        "the year 2018, with wind speed, active power, the theoretical power curve, and wind "
        "direction. The theoretical power curve is used only to derive physically meaningful "
        "knots and to flag outliers; it is never used as a model feature, which avoids leakage."
    )
    para(doc, text, size=12, line=1.5, after=8)
    text2 = (
        "The spline knots are placed at the detected cut-in speed of 3.0 m/s and the rated "
        "speed of 13.0 m/s. Five cleaning rules remove negative power, over-rated power, "
        "downtime, sustained underperformance, and robust within-bin outliers, retaining 44,306 "
        "of the original 50,530 observations. Eight models are compared under identical "
        "five-fold cross-validation: a mean baseline, linear regression, a cubic polynomial, "
        "piecewise linear, cubic B-spline, natural cubic spline, penalized spline with RidgeCV, "
        "and a hybrid physical spline. The spline basis is fitted inside each training fold so "
        "that the validation fold is never seen during fitting. The hybrid physical spline is "
        "the best model, with a cross-validated RMSE of 103.89 kW, MAE of 63.38 kW, and R\u00b2 "
        "of 0.9935, reducing RMSE by roughly 67 percent compared with linear regression. A "
        "chronological TimeSeriesSplit confirms the ranking. Diagnostic plots, regime-wise "
        "errors, and a six-tab Streamlit dashboard make the analysis reproducible and "
        "interactive. The work maps directly to Module 4, Resampling Methods, and supports "
        "SDG 7, Affordable and Clean Energy."
    )
    para(doc, text2, size=12, line=1.5, after=8)


TOC_ROWS = [
    ("", "Certificate", "i"),
    ("", "Acknowledgement", "ii"),
    ("", "Abstract", "iii"),
    ("1", "Introduction", "00-00"),
    ("", "Preamble", ""),
    ("", "Problem Statement", ""),
    ("", "Aim and Objectives of the Proposed Work", ""),
    ("", "Proposed System", ""),
    ("", "Block Diagram of the Proposed System", ""),
    ("2", "Literature Survey", "00-00"),
    ("3", "System Requirement and Specification", "00-00"),
    ("", "Hardware and Software Requirements", ""),
    ("4", "System Architecture and Implementation", "00-00"),
    ("", "Methodology", ""),
    ("5", "Results and Discussion", "00-00"),
    ("6", "Advantages, Disadvantages and Applications", "00-00"),
    ("", "Advantages", ""),
    ("", "Disadvantages", ""),
    ("", "Applications", ""),
    ("7", "Conclusion and Future Scope", "00-00"),
    ("", "References", "00"),
]


def table_of_contents(doc):
    h = para(doc, "TABLE OF CONTENTS", size=18, bold=True,
             align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=12)
    h.paragraph_format.page_break_before = True
    add_bookmark(h, "bm_toc", 4)
    table = borderless_table(doc, len(TOC_ROWS) + 1, 3)
    remove_table_borders(table)
    set_cell(table.rows[0].cells[0], "Chapter No.", size=11.5, bold=True,
             align=WD_ALIGN_PARAGRAPH.CENTER)
    set_cell(table.rows[0].cells[1], "Contents", size=11.5, bold=True,
             align=WD_ALIGN_PARAGRAPH.CENTER)
    set_cell(table.rows[0].cells[2], "Page No.", size=11.5, bold=True,
             align=WD_ALIGN_PARAGRAPH.CENTER)
    for i, (num, content, page) in enumerate(TOC_ROWS, start=1):
        row = table.rows[i]
        is_chapter = bool(num)
        set_cell(row.cells[0], num, size=11.5, bold=is_chapter,
                 align=WD_ALIGN_PARAGRAPH.CENTER)
        set_cell(row.cells[1], content, size=11.5, bold=is_chapter,
                 align=WD_ALIGN_PARAGRAPH.LEFT)
        set_cell(row.cells[2], page, size=11.5, bold=is_chapter,
                 align=WD_ALIGN_PARAGRAPH.RIGHT)
        if not is_chapter:
            row.cells[1].paragraphs[0].paragraph_format.left_indent = Inches(0.3)
    set_col_widths(table, [Inches(1.15), Inches(4.85), Inches(0.85)])


def chapter1(doc):
    chapter(doc, 1, "INTRODUCTION", "bm_ch1", 5, new_page=False)
    para(
        doc,
        "Wind energy is one of the fastest-growing renewable sources, and grid operators rely "
        "on an accurate power curve to forecast generation, detect underperformance, and plan "
        "maintenance. The power curve of a wind turbine is strongly non-linear: the machine "
        "stays idle below the cut-in speed, produces power at a steeply increasing rate through "
        "the ramp region, and then saturates at rated power. A single straight-line fit cannot "
        "represent these three regimes and therefore produces large errors exactly where "
        "forecasts matter most. This project models the power curve with spline regression, "
        "using knots at the two physically meaningful speeds, and evaluates the model with "
        "resampling methods.",
        size=12, line=1.5, after=8,
    )
    para(doc, "The project delivers the following capabilities:", size=12, line=1.5, after=4)
    for text in [
        "Spline regression with knots at the detected cut-in and rated wind speeds.",
        "Five physically motivated and robust rules for cleaning invalid observations.",
        "Five-fold cross-validation for an unbiased comparison of eight competing models.",
        "Diagnostic plots, regime-wise error analysis, and influence diagnostics.",
        "An interactive Streamlit dashboard that exposes every modelling choice to the user.",
    ]:
        bullet(doc, text)

    heading(doc, "Preamble", size=16, before=12, after=6)
    para(
        doc,
        "Wind turbines convert the kinetic energy of moving air into electrical power. The "
        "relationship between wind speed and active power is governed by the turbine's "
        "aerodynamic design and by its control strategy. Below the cut-in speed there is not "
        "enough torque to rotate the rotor, so the output is effectively zero. Between cut-in "
        "and rated speed the turbine follows the available wind power, which rises roughly with "
        "the cube of wind speed, giving the characteristic S-shaped ramp. Above the rated speed "
        "the pitch controller limits the output to the machine rating, producing a flat "
        "plateau.",
        size=12, line=1.5, after=8,
    )
    para(
        doc,
        "Because these three regimes have different physical meanings, a model should respect "
        "them rather than smooth across them. Spline regression is well suited to this task: it "
        "represents the curve as a weighted sum of local polynomial basis functions that are "
        "joined smoothly at chosen knots. Placing the knots at cut-in and rated speed gives the "
        "model flexibility inside the ramp region while keeping the fitted curve stable in the "
        "idle and rated regions.",
        size=12, line=1.5, after=8,
    )
    para(
        doc,
        "The project uses the public T1.csv SCADA dataset, which contains ten-minute "
        "observations from a single turbine for the whole of 2018. Besides the measured active "
        "power and wind speed, the dataset includes a theoretical power curve supplied by the "
        "manufacturer. This reference curve is used to detect the physical knots and to flag "
        "underperformance, but it is deliberately excluded from the model features because it is "
        "a deterministic function of wind speed and would leak the target.",
        size=12, line=1.5, after=8,
    )

    heading(doc, "Problem Statement", size=16, before=12, after=6)
    para(
        doc,
        "Grid operators and asset managers need a reliable estimate of expected power at every "
        "wind speed. In practice, however, raw SCADA data contain measurement errors, downtime, "
        "curtailment, and de-rated operation. These observations distort the fitted curve and "
        "inflate forecast error. A naive straight-line or low-order polynomial fit is not "
        "sufficient because it cannot represent the cut-in region, the steep ramp, and the "
        "rated plateau at the same time. The problem addressed by this project is therefore to "
        "build a physically interpretable, statistically validated power-curve model that is "
        "robust to invalid observations and whose performance is estimated on unseen data.",
        size=12, line=1.5, after=8,
    )
    para(doc, "The main difficulties are:", size=12, line=1.5, after=4)
    for text in [
        "Capturing the S-shaped ramp and the rated plateau with a single interpretable model.",
        "Choosing knots from the data rather than from an arbitrary grid.",
        "Removing downtime, curtailment, and measurement errors without deleting genuine "
        "low-wind zeros.",
        "Estimating test error honestly when observations are not independent.",
        "Comparing competing models fairly under identical cleaning and resampling settings.",
    ]:
        bullet(doc, text)

    heading(doc, "Aim and Objectives of the Proposed Work", size=16, before=12, after=6)
    para(
        doc,
        "Aim: The aim of this project is to design and develop a reproducible spline-regression "
        "framework that models the wind-turbine power curve with knots at the cut-in and rated "
        "wind speeds, cleans physically invalid observations, and compares competing models "
        "using cross-validation. The framework is delivered through an interactive dashboard so "
        "that every modelling decision can be inspected and reproduced.",
        size=12, line=1.5, after=8,
    )
    para(doc, "Objectives:", size=12, bold=True, line=1.5, after=4)
    objectives = [
        "To detect the cut-in and rated wind speeds from the theoretical power curve and use "
        "them as physically meaningful spline knots.",
        "To implement five cleaning rules that remove negative power, over-rated power, "
        "downtime, sustained underperformance, and robust within-bin outliers.",
        "To build and compare eight regression models, from a mean baseline and linear "
        "regression to cubic, natural, penalized, and hybrid spline models.",
        "To evaluate every model with five-fold cross-validation, fitting the spline basis "
        "inside each training fold to prevent data leakage.",
        "To analyse the selected model with residual, Q-Q, influence, and regime-wise "
        "diagnostics, and to expose the complete workflow through a Streamlit dashboard.",
    ]
    for i, text in enumerate(objectives, start=1):
        numbered(doc, i, text)

    heading(doc, "Proposed System", size=16, before=12, after=6)
    para(
        doc,
        "The proposed system is a Python-based statistical machine learning platform. It "
        "combines a data layer, a preprocessing layer, a model bank, an evaluation layer, and a "
        "presentation layer. The data layer parses the raw SCADA file, removes duplicate "
        "timestamps, and validates the required columns. The preprocessing layer derives the "
        "physical knots and applies the cleaning rules. The model bank contains the eight "
        "regressors. The evaluation layer runs cross-validation, computes error metrics, and "
        "produces diagnostics. The presentation layer is a six-tab Streamlit dashboard.",
        size=12, line=1.5, after=6,
    )
    figure(doc, FIG / "fig_block_diagram.png", 6.85,
           "Fig 1.1: Block diagram of the proposed system")
    para(doc, "Core system components:", size=12, bold=True, line=1.5, after=4)
    for text in [
        "Data and validation module: loads T1.csv, parses timestamps, removes duplicates, and "
        "reports data-quality checks.",
        "Preprocessing module: detects cut-in and rated speeds, flags outliers, and produces "
        "the cleaned dataset.",
        "Model bank: implements mean, linear, polynomial, piecewise linear, cubic B-spline, "
        "natural cubic spline, penalized spline, and hybrid physical spline models.",
        "Evaluation module: performs K-fold and time-series cross-validation, computes RMSE, "
        "MAE, R\u00b2, sMAPE and MAPE, and produces regime-wise errors.",
        "Visualisation and presentation: interactive Plotly figures plus a six-tab Streamlit "
        "frontend with sidebar controls for knots, cleaning rules, folds, seed, and model selection.",
    ]:
        bullet(doc, text)
    para(doc, "Performance specifications:", size=12, bold=True, line=1.5, after=4)
    for text in [
        "Target variable: LV ActivePower (kW); input feature: Wind Speed (m/s).",
        "Dataset size: 50,530 ten-minute observations covering the full year 2018.",
        "Physical knots: cut-in 3.0 m/s and rated 13.0 m/s; rated power 3,600 kW.",
        "Validation: five-fold K-fold (seed 42) plus a chronological TimeSeriesSplit.",
        "Primary metric: RMSE in kW, supported by MAE, R\u00b2, sMAPE and MAPE.",
    ]:
        bullet(doc, text)


def chapter2(doc):
    chapter(doc, 2, "Literature Survey", "bm_ch2", 6)
    para(
        doc,
        "The literature relevant to this project spans three areas: spline and penalized "
        "regression, resampling methods for model assessment, and wind-turbine power-curve "
        "modelling. The table below summarises ten representative works, the problem each "
        "addresses, the gap that remains, and how the present project addresses that gap.",
        size=12, line=1.5, after=8,
    )
    rows = [
        ["[1]", "Spline Models for Observational Data",
         "SIAM, 1990 \u2014 G. Wahba",
         "Parametric curves impose a rigid global shape and cannot represent local non-linearity in the power curve.",
         "Presents smoothing theory but does not apply spline bases to turbine SCADA data or cross-validated model selection.",
         "Cubic B-spline bases with knots at cut-in and rated speed are compared against parametric baselines."],
        ["[2]", "Smoothing Noisy Data with Spline Functions",
         "Numerische Mathematik, 1979 \u2014 P. Craven, G. Wahba",
         "Unpenalized splines overfit noisy observations, and the smoothing parameter is difficult to choose.",
         "Theoretical treatment without physical constraints or a practical pipeline for power curves.",
         "A penalized spline with RidgeCV selects smoothness by cross-validation; the hybrid model enforces physical bounds."],
        ["[3]", "The Elements of Statistical Learning",
         "Springer, 2009 \u2014 T. Hastie, R. Tibshirani, J. Friedman",
         "Linear models underfit non-linear relationships, while very flexible models may overfit.",
         "General methodology, not specific to wind power or operational constraints.",
         "The bias-variance framework guides the comparison of eight models using out-of-fold error."],
        ["[4]", "An Introduction to Statistical Learning",
         "Springer, 2021 \u2014 G. James, D. Witten, T. Hastie, R. Tibshirani",
         "Training error underestimates test error, so model assessment requires resampling.",
         "Textbook treatment without turbine-specific leakage controls.",
         "Five-fold CV with the spline basis fitted inside each fold; a chronological split is added as a check."],
        ["[5]", "Cross-Validatory Choice and Assessment of Statistical Predictions",
         "JRSS-B, 1974 \u2014 M. Stone",
         "Model selection based on in-sample fit is optimistic and can mislead.",
         "Theoretical work with no guidance for multi-model energy pipelines.",
         "K-fold CV ranks all models and reports the mean and standard deviation across folds."],
        ["[6]", "A Study of Cross-Validation and Bootstrap for Accuracy Estimation",
         "IJCAI, 1995 \u2014 R. Kohavi",
         "The choice of resampling scheme materially affects accuracy estimates.",
         "Benchmarked classification tasks rather than regression on SCADA data.",
         "A fixed seed, five folds, and fold-level spread are reported; robustness is checked with TimeSeriesSplit."],
        ["[7]", "On-line Monitoring of Power Curves",
         "Renewable Energy, 2009 \u2014 A. Kusiak, H. Zheng, Z. Song",
         "Turbine monitoring needs an accurate normal-behaviour power curve to detect underperformance.",
         "Uses neural and parametric models without spline knots or robust outlier rules.",
         "A spline model with physical knots plus five cleaning rules, including a MAD-based rule."],
        ["[8]", "A Comprehensive Review on Wind Turbine Power Curve Modeling Techniques",
         "RSER, 2014 \u2014 M. Lydia et al.",
         "Many parametric models cannot represent the S-shape and the plateau simultaneously.",
         "Review only; no reproducible open implementation.",
         "A reproducible Python pipeline and an interactive Streamlit dashboard are provided."],
        ["[9]", "Review of Power Curve Modelling for Wind Turbines",
         "RSER, 2013 \u2014 C. Carrillo et al.",
         "Power-curve models differ widely in accuracy and data requirements.",
         "No systematic cross-validated comparison under identical cleaning.",
         "Eight models are compared under identical cleaning and five-fold CV settings."],
        ["[10]", "On the Use of Cross-Validation for Time Series Predictor Evaluation",
         "Information Sciences, 2012 \u2014 C. Bergmeir, J. M. Ben\u00edtez",
         "Random CV can be invalid when observations are temporally dependent.",
         "General time-series evaluation, not applied to power-curve regression.",
         "Both shuffled K-fold and chronological TimeSeriesSplit results are reported."],
    ]
    data_table(
        doc,
        ["Sl. No.", "Paper Name", "Journal / Author", "Problem Statement",
         "Gap in the Paper", "How Gap is Addressed by Our Project"],
        rows,
        [Inches(0.42), Inches(1.30), Inches(1.12), Inches(1.32), Inches(1.32), Inches(1.37)],
        font_size=8.3,
        header_size=8.6,
    )
    para(doc, "", size=6, line=1.0, after=0)
    para(
        doc,
        "The survey shows a consistent gap: spline methodology is well developed, and power-"
        "curve reviews are extensive, but there is little work that combines physically placed "
        "knots, robust cleaning, and leakage-free cross-validation in a single reproducible "
        "pipeline. This project fills that gap.",
        size=12, line=1.5, after=8,
    )


def chapter3(doc):
    chapter(doc, 3, "System Requirement and Specification", "bm_ch3", 7)
    heading(doc, "3.1 Hardware Requirements", size=16, before=6, after=6)
    para(
        doc,
        "The workload is a statistical regression pipeline on a 50,530-row tabular dataset. It "
        "does not require a GPU, but a modern multi-core processor and sufficient memory make "
        "cross-validation responsive.",
        size=12, line=1.5, after=6,
    )
    for text in [
        "Processor (CPU): Intel Core i5 (8th generation or above) or AMD Ryzen 5 or an "
        "equivalent multi-core processor.",
        "Memory (RAM): Minimum 8 GB; 16 GB is recommended for comfortable execution of the "
        "Streamlit dashboard alongside cross-validation.",
        "Storage: Minimum 2 GB of free disk space for the dataset, virtual environment, and "
        "generated figures and metrics.",
        "Display: A standard 1920 \u00d7 1080 display or higher for the interactive dashboard.",
        "Peripherals: A standard keyboard and mouse; no special audio or sensor hardware is "
        "required.",
    ]:
        bullet(doc, text)

    heading(doc, "3.2 Software Requirements and Technology Stack", size=16, before=12, after=6)
    para(
        doc,
        "The platform is built on a Python-native scientific computing stack. The exact "
        "versions are pinned in requirements.txt so that results are reproducible.",
        size=12, line=1.5, after=6,
    )
    for text in [
        "Operating System: Windows 10/11 or Linux (Ubuntu 20.04 or later).",
        "Programming Language: Python 3.10 or later.",
        "Data Handling: pandas 2.3.3, NumPy 2.2.6, SciPy 1.15.3.",
        "Machine Learning: scikit-learn 1.7.2 (spline transformers, RidgeCV, pipelines, "
        "cross-validation), statsmodels 0.15.0, patsy 1.0.3.",
        "Visualisation: Plotly 7.1.0, Matplotlib 3.10.9, Seaborn 0.13.2.",
        "Frontend: Streamlit 1.65.0 with custom CSS injection.",
        "Persistence: joblib 1.6.0 for saving the selected model.",
        "Development Tools: Visual Studio Code, Git and GitHub.",
    ]:
        bullet(doc, text)

    heading(doc, "3.3 Dataset Specification", size=16, before=12, after=6)
    para(
        doc,
        "The dataset T1.csv contains ten-minute SCADA observations from a wind turbine for the "
        "year 2018. The timestamp is used for ordering, duplicate removal, and time-series "
        "checks. The active power is the target, wind speed is the only model feature, the "
        "theoretical power curve is used only for knot detection and outlier checks, and wind "
        "direction is descriptive. The theoretical curve is never used as a model feature, which "
        "avoids leakage.",
        size=12, line=1.5, after=6,
    )


def chapter4(doc):
    chapter(doc, 4, "System Architecture and Implementation", "bm_ch4", 8)
    heading(doc, "4.1 Methodology", size=16, before=6, after=6)

    heading(doc, "4.1.1 Problem Analysis and Requirement Gathering", size=14, before=6, after=4)
    para(
        doc,
        "The analysis identified three requirements. First, the model must represent the cut-in "
        "region, the ramp, and the rated plateau without fitting a separate curve for every "
        "wind speed. Second, the pipeline must remove invalid observations while retaining "
        "genuine zero-power readings below cut-in. Third, model performance must be estimated "
        "on unseen data, because in-sample error is optimistic for flexible spline models.",
        size=12, line=1.5, after=6,
    )

    heading(doc, "4.1.2 Dataset and Preprocessing", size=14, before=6, after=4)
    para(
        doc,
        "The raw file is read with UTF-8 BOM handling, the first five columns are renamed to "
        "canonical names, timestamps are parsed, rows with missing timestamps or missing target "
        "values are dropped, and duplicate timestamps are removed. The cleaned frame is sorted "
        "chronologically. The validation step confirms 50,530 rows, zero duplicate timestamps, "
        "and zero missing values in the main columns.",
        size=12, line=1.5, after=6,
    )

    heading(doc, "4.1.3 Knot Detection and Physical Constraints", size=14, before=6, after=4)
    para(
        doc,
        "Knots are derived from the theoretical power curve rather than chosen by hand. The "
        "cut-in speed is the first wind speed at which the theoretical power becomes positive, "
        "which yields 3.0 m/s. The rated speed is the first wind speed at which the theoretical "
        "power reaches its maximum, which yields 13.0 m/s. The rated power is the rounded "
        "maximum of the theoretical curve, 3,600 kW. Additional boundary knots at 0 m/s and "
        "26 m/s keep the spline stable across the observed range. The sidebar allows the user to "
        "override all three values.",
        size=12, line=1.5, after=6,
    )

    heading(doc, "4.1.4 Spline Regression Formulation", size=14, before=6, after=4)
    para(
        doc,
        "A spline represents the power curve as a weighted sum of local basis functions:",
        size=12, line=1.5, after=4,
    )
    para(
        doc,
        "power = \u03b2\u2080 + \u03b2\u2081B\u2081(wind_speed) + \u03b2\u2082B\u2082(wind_speed) + \u2026 + \u03b2\u209aB\u209a(wind_speed) + error",
        size=12, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, line=1.5, after=6,
    )
    para(
        doc,
        "The basis functions are cubic polynomials joined smoothly at the knots. This gives the "
        "model enough flexibility to capture the S-shape and the plateau without the "
        "oscillation of a high-degree global polynomial. A natural cubic spline adds the "
        "constraint that the curve is linear beyond the boundary knots, which stabilises "
        "extrapolation. A penalized spline uses many basis functions with a ridge penalty, and "
        "the penalty strength is selected by cross-validation.",
        size=12, line=1.5, after=6,
    )

    heading(doc, "4.1.5 Model Bank", size=14, before=6, after=4)
    para(
        doc,
        "Eight models are included so that the contribution of spline structure can be isolated. "
        "All predictions are clipped to the physical operating envelope: zero below cut-in, the "
        "fitted value in the ramp region, and rated power at and above rated speed.",
        size=12, line=1.5, after=6,
    )
    rows = [
        ["Mean baseline", "Predicts the average power for every wind speed; lower-bound reference."],
        ["Linear regression", "Straight-line fit; demonstrates why a global line fails."],
        ["Polynomial (degree 3)", "Global cubic curve; flexible but can oscillate at the edges."],
        ["Piecewise linear", "Linear segments joined at the cut-in and rated knots."],
        ["Cubic B-spline", "Smooth cubic basis with knots at cut-in and rated speed."],
        ["Natural cubic spline", "Cubic spline constrained to be linear beyond the boundary knots."],
        ["Penalized spline (RidgeCV)", "Many basis functions with a cross-validated smoothness penalty."],
        ["Hybrid physical spline", "Zero below cut-in, spline in the ramp, constant above rated speed."],
    ]
    data_table(doc, ["Model", "Purpose"], rows, [Inches(2.25), Inches(4.60)],
               font_size=10, header_size=10)

    heading(doc, "4.1.6 Outlier Handling", size=14, before=8, after=4)
    para(
        doc,
        "Five rules are applied, and each is exposed as a toggle in the dashboard so that its "
        "effect can be measured rather than assumed.",
        size=12, line=1.5, after=4,
    )
    for text in [
        "Negative active power: a measurement error and therefore removed.",
        "Power above the rated limit: a measurement spike or scaling error.",
        "Zero power above cut-in: turbine downtime, curtailment, or de-rating.",
        "Underperformance against the theoretical curve: sustained de-rated operation.",
        "Robust MAD rule within each 0.5 m/s wind-speed bin: removes extreme scatter using the "
        "median absolute deviation.",
    ]:
        bullet(doc, text)
    para(
        doc,
        "Genuine zero-power readings below cut-in are retained because they are physically "
        "valid. The default settings remove 6,224 of 50,530 observations, leaving 44,306 "
        "records for modelling.",
        size=12, line=1.5, after=6,
    )
    figure(doc, FIG / "fig_outliers.png", 5.5,
           "Fig 4.1: Outlier rules and the number of flagged observations")
    figure(doc, FIG / "fig_cleaning.png", 5.7,
           "Fig 4.2: Operating envelope before and after outlier cleaning")

    heading(doc, "4.1.7 Cross-Validation Protocol", size=14, before=6, after=4)
    para(
        doc,
        "The default is five-fold shuffled K-fold cross-validation with a fixed random seed of "
        "42. The spline basis is fitted inside each training fold, so the validation fold is "
        "never seen during fitting. Each model is cloned and refitted for every fold, and the "
        "reported metrics are the mean and standard deviation across folds. The training script "
        "also runs a chronological TimeSeriesSplit as a robustness check for temporal "
        "dependence.",
        size=12, line=1.5, after=6,
    )
    para(doc, "Metrics:", size=12, bold=True, line=1.5, after=4)
    for text in [
        "RMSE: the primary comparison metric, expressed in kW.",
        "MAE: average absolute error, less sensitive to large residuals.",
        "R\u00b2: proportion of variance explained.",
        "sMAPE and MAPE: percentage-style errors, with MAPE excluding near-zero power rows.",
    ]:
        bullet(doc, text)

    heading(doc, "4.1.8 Implementation and Development Workflow", size=14, before=6, after=4)
    for i, text in enumerate([
        "Load and validate the SCADA dataset, then detect the physical knots.",
        "Apply the cleaning rules and produce the modelling frame.",
        "Fit and compare the eight models inside the cross-validation loop.",
        "Select the best model by mean cross-validated RMSE.",
        "Generate residual, Q-Q, influence, and regime-wise diagnostics.",
        "Expose the full workflow through the six-tab Streamlit dashboard.",
    ], start=1):
        numbered(doc, i, text)

    heading(doc, "4.1.9 Testing and Validation", size=14, before=6, after=4)
    para(
        doc,
        "Unit checks confirmed that knot detection returns 3.0 and 13.0 m/s, that the cleaning "
        "rules reproduce the expected flag counts, and that predictions respect the physical "
        "envelope. Performance testing confirmed that the five-fold comparison of eight models "
        "runs on a standard laptop. Leakage testing confirmed that the spline basis is refitted "
        "inside every fold, and the chronological split reproduced the same ranking, so the "
        "result is not an artefact of random shuffling.",
        size=12, line=1.5, after=6,
    )


def chapter5(doc):
    chapter(doc, 5, "Results and Discussion", "bm_ch5", 9)

    heading(doc, "5.1 Dataset and Cleaning Results", size=16, before=6, after=6)
    para(
        doc,
        "The raw dataset contains 50,530 ten-minute observations from 1 January 2018 to 31 "
        "December 2018. Wind speed ranges from 0.0 to 25.2 m/s and active power from \u22122.47 "
        "to 3,618.73 kW. There are no missing values and no duplicate timestamps in the five "
        "main columns. The cleaning stage removes 6,224 observations, or 12.3 percent of the "
        "data, leaving 44,306 records.",
        size=12, line=1.5, after=6,
    )
    rows = [
        ["Rows", "50,530"],
        ["Columns", "8"],
        ["Time range", "01 Jan 2018 to 31 Dec 2018"],
        ["Duplicate timestamps", "0"],
        ["Missing values", "0"],
        ["Negative power readings", "57"],
        ["Zero power readings", "10,781"],
        ["Zero power above 3 m/s", "3,497"],
    ]
    para(doc, "Table 5.1: Data-quality summary", size=10.5, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=3, keep_next=True)
    data_table(doc, ["Check", "Value"], rows, [Inches(3.4), Inches(3.0)],
               font_size=10, header_size=10)
    para(doc, "", size=6, line=1.0, after=0)

    rows = [
        ["Negative active power", "57", "57", "Yes"],
        ["Power above rated limit", "0", "0", "Yes"],
        ["Zero power above cut-in (downtime)", "3,545", "3,545", "Yes"],
        ["Underperformance vs theoretical curve", "2,868", "2,868", "Yes"],
        ["Statistical outlier within wind bin (MAD)", "3,952", "3,952", "Yes"],
        ["Total removed (union of rules)", "6,224", "6,224", "\u2014"],
    ]
    para(doc, "Table 5.2: Outlier-rule summary", size=10.5, bold=True,
         align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=3, keep_next=True)
    data_table(doc, ["Rule", "Flagged", "Removed", "Enabled"], rows,
               [Inches(3.55), Inches(1.0), Inches(1.0), Inches(0.9)],
               font_size=10, header_size=10)

    heading(doc, "5.2 Model Comparison Results", size=16, before=12, after=6)
    para(
        doc,
        "Table 5.3 reports the five-fold cross-validated performance of all eight models. The "
        "hybrid physical spline ranks first with an RMSE of 103.89 kW, an MAE of 63.38 kW, and "
        "an R\u00b2 of 0.9935. The penalized spline is effectively tied, which shows that the "
        "gain comes from the spline structure rather than from a particular basis. Linear "
        "regression is far worse, with an RMSE of 313.63 kW, because it cannot represent the "
        "three operating regimes.",
        size=12, line=1.5, after=6,
    )
    rows = [
        ["1", "Hybrid physical spline", "103.89", "63.38", "0.9935", "9.65"],
        ["2", "Penalized spline (RidgeCV)", "103.91", "63.40", "0.9935", "9.65"],
        ["3", "Cubic B-spline (knots at cut-in and rated)", "110.79", "72.67", "0.9927", "19.48"],
        ["4", "Natural cubic spline (knots at cut-in and rated)", "118.79", "77.28", "0.9916", "17.04"],
        ["5", "Polynomial (degree 3)", "147.74", "99.56", "0.9869", "15.36"],
        ["6", "Piecewise linear (knots at cut-in and rated)", "168.95", "120.40", "0.9829", "25.79"],
        ["7", "Linear regression", "313.63", "237.62", "0.9411", "31.38"],
        ["8", "Mean baseline", "1,292.70", "1,140.51", "\u22120.0002", "99.01"],
    ]
    para(doc, "Table 5.3: Cross-validated model comparison (5-fold, seed 42)",
         size=10.5, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=3,
         keep_next=True)
    data_table(doc, ["Rank", "Model", "CV RMSE (kW)", "CV MAE (kW)", "CV R\u00b2", "CV sMAPE (%)"],
               rows,
               [Inches(0.55), Inches(2.55), Inches(1.0), Inches(1.0), Inches(0.85), Inches(0.95)],
               font_size=10, header_size=10)
    para(doc, "", size=6, line=1.0, after=0)
    figure(doc, FIG / "fig_cv_boxplot.png", 6.3,
           "Fig 5.1: Fold-level RMSE distribution across models")

    heading(doc, "5.3 Selected Model and Fitted Power Curve", size=16, before=8, after=6)
    para(
        doc,
        "Figure 5.2 shows the hybrid physical spline fitted to the cleaned data. The model "
        "returns zero below 3.0 m/s, follows the observed ramp between 3.0 and 13.0 m/s, and "
        "holds the rated power of 3,600 kW above 13.0 m/s. The spline stays smooth through the "
        "ramp and does not oscillate in the idle or rated regions. The comparison in Figure 5.3 "
        "shows why the choice of model matters: the linear fit over-predicts at low wind speeds "
        "and under-predicts near rated power, while the spline models track the observed "
        "envelope.",
        size=12, line=1.5, after=6,
    )
    figure(doc, FIG / "fig_power_curve.png", 6.3,
           "Fig 5.2: Fitted power curve with cut-in and rated knots (best model)")
    figure(doc, FIG / "fig_model_comparison.png", 6.3,
           "Fig 5.3: Comparison of the fitted power-curve models")

    heading(doc, "5.4 Diagnostic Analysis", size=16, before=8, after=6)
    para(
        doc,
        "All diagnostics use out-of-fold predictions, so they reflect unseen data. Figure 5.4 "
        "shows that the residuals are centred on zero and roughly symmetric. The Q-Q plot in "
        "Figure 5.5 shows heavier tails than a normal distribution, which is expected because "
        "the ramp region contains genuine variability that no single wind-speed model can "
        "explain. Figure 5.6 confirms that predictions follow the ideal line closely, with the "
        "largest scatter in the steep part of the ramp.",
        size=12, line=1.5, after=6,
    )
    figure(doc, FIG / "fig_residuals.png", 6.4,
           "Fig 5.4: Residuals versus fitted values and residual distribution")
    figure(doc, FIG / "fig_qq.png", 4.35,
           "Fig 5.5: Normal Q-Q plot of out-of-fold residuals")
    figure(doc, FIG / "fig_actual_pred.png", 4.75,
           "Fig 5.6: Actual versus predicted power")

    para(
        doc,
        "Table 5.4 breaks the error down by operating regime. The below-cut-in region has a "
        "very low RMSE of 3.12 kW because the model correctly predicts zero. The ramp region "
        "carries most of the error, with an RMSE of 121.04 kW, which is consistent with the "
        "steep slope and natural wind variability in that region. The rated region has a low "
        "RMSE of 24.06 kW. The negative R\u00b2 values in the flat regions are not a concern: "
        "when the variance of the target is almost zero, R\u00b2 becomes unstable, and MAE is "
        "the more meaningful measure there.",
        size=12, line=1.5, after=6,
    )
    rows = [
        ["Below cut-in", "7,709", "3.12", "0.48", "\u22120.0246"],
        ["Ramp region", "32,477", "121.04", "85.01", "0.9878"],
        ["Rated region", "4,120", "24.06", "10.51", "\u22120.0968"],
    ]
    para(doc, "Table 5.4: Regime-wise error of the best model",
         size=10.5, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=3,
         keep_next=True)
    data_table(doc, ["Regime", "Samples", "RMSE (kW)", "MAE (kW)", "R\u00b2"], rows,
               [Inches(1.6), Inches(1.0), Inches(1.1), Inches(1.0), Inches(0.9)],
               font_size=10, header_size=10)
    para(doc, "", size=6, line=1.0, after=0)
    figure(doc, FIG / "fig_regime_errors.png", 5.9,
           "Fig 5.7: Error by operating regime for the best model")

    heading(doc, "5.5 Effect of Outlier Cleaning", size=16, before=8, after=6)
    para(
        doc,
        "Table 5.5 compares each model on the raw and cleaned data. Cleaning reduces the "
        "cross-validated RMSE of the hybrid spline from 393.87 kW to 103.89 kW, a reduction of "
        "73.6 percent. The improvement is even larger than the gain from changing the model, "
        "which confirms that downtime and curtailment observations would otherwise dominate the "
        "error.",
        size=12, line=1.5, after=6,
    )
    rows = [
        ["Hybrid physical spline", "393.87", "103.89", "73.6%"],
        ["Cubic B-spline (knots at cut-in and rated)", "397.50", "110.79", "72.1%"],
        ["Linear regression", "482.55", "313.63", "35.0%"],
    ]
    para(doc, "Table 5.5: Cleaning impact on cross-validated RMSE",
         size=10.5, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=3,
         keep_next=True)
    data_table(doc, ["Model", "Raw-data RMSE (kW)", "Cleaned-data RMSE (kW)", "Reduction"],
               rows, [Inches(2.6), Inches(1.4), Inches(1.55), Inches(1.0)],
               font_size=10, header_size=10)

    heading(doc, "5.6 Time-Series Robustness Check", size=16, before=12, after=6)
    para(
        doc,
        "Random K-fold cross-validation ignores temporal dependence. The training script "
        "therefore repeats the comparison with a chronological TimeSeriesSplit. Table 5.6 shows "
        "that the ranking is unchanged: the hybrid physical spline remains the best model, with "
        "a time-ordered RMSE of 110.08 kW. This confirms that the result is not an artefact of "
        "shuffling.",
        size=12, line=1.5, after=6,
    )
    rows = [
        ["Hybrid physical spline", "110.08", "67.50", "0.9917"],
        ["Penalized spline (RidgeCV)", "110.13", "67.50", "0.9917"],
        ["Cubic B-spline (knots at cut-in and rated)", "115.58", "76.05", "0.9909"],
        ["Natural cubic spline (knots at cut-in and rated)", "123.89", "82.85", "0.9897"],
        ["Polynomial (degree 3)", "163.96", "116.99", "0.9820"],
        ["Piecewise linear (knots at cut-in and rated)", "183.69", "132.13", "0.9767"],
        ["Linear regression", "337.16", "260.18", "0.9237"],
        ["Mean baseline", "1,283.30", "1,134.29", "\u22120.0822"],
    ]
    para(doc, "Table 5.6: Chronological TimeSeriesSplit results",
         size=10.5, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=3,
         keep_next=True)
    data_table(doc, ["Model", "Time RMSE (kW)", "Time MAE (kW)", "Time R\u00b2"], rows,
               [Inches(2.7), Inches(1.3), Inches(1.3), Inches(1.0)],
               font_size=10, header_size=10)

    heading(doc, "5.7 Interactive Dashboard", size=16, before=12, after=6)
    para(
        doc,
        "The six-tab Streamlit dashboard makes the complete workflow interactive. The sidebar "
        "exposes the dataset, the physical knots, the outlier rules, the MAD threshold, the "
        "number of folds, the random seed, and the model list, so every result in this chapter "
        "can be reproduced from the interface. The screenshots below show each tab as rendered "
        "by the dashboard.",
        size=12, line=1.5, after=6,
    )
    for name, caption in [
        ("dash_01_overview.png",
         "Fig 5.8: Overview tab \u2014 dataset summary, data-quality checks, and distributions"),
        ("dash_02_cleaning.png",
         "Fig 5.9: Cleaning & outliers tab \u2014 rule-wise counts and before/after scatter"),
        ("dash_03_power_curve.png",
         "Fig 5.10: Power curve tab \u2014 fitted B-spline with cut-in and rated knots"),
        ("dash_04_model_comparison.png",
         "Fig 5.11: Model comparison tab \u2014 cross-validated metrics and fold-level RMSE"),
        ("dash_05_diagnostics.png",
         "Fig 5.12: Diagnostics tab \u2014 out-of-fold residual and distribution plots"),
        ("dash_06_methodology.png",
         "Fig 5.13: Methodology tab \u2014 method summary and Module 4 mapping"),
    ]:
        figure(doc, FIG / name, 6.4, caption)

    heading(doc, "5.8 Discussion", size=16, before=12, after=6)
    para(
        doc,
        "The results support three conclusions. First, model structure matters: spline models "
        "reduce cross-validated RMSE by roughly 67 percent compared with linear regression. "
        "Second, cleaning matters even more: removing downtime, curtailment, and measurement "
        "errors cuts the error of the best model by almost three quarters. Third, the physical "
        "constraints are valuable: the hybrid model, which enforces zero below cut-in and rated "
        "power above rated speed, is the best and the easiest to explain. The near-tie with the "
        "penalized spline shows that the gain comes from the spline basis itself, while the "
        "hybrid structure adds interpretability at no cost in accuracy.",
        size=12, line=1.5, after=8,
    )
    para(
        doc,
        "The regime analysis adds an important qualification. Most of the remaining error comes "
        "from the ramp region, where a small change in wind speed produces a large change in "
        "power. This is a physical limit of a univariate model rather than a defect of the "
        "spline. Including wind direction, air density, turbulence intensity, and yaw "
        "misalignment would be the natural next step.",
        size=12, line=1.5, after=8,
    )

    heading(doc, "5.9 Limitations", size=16, before=6, after=6)
    for text in [
        "The model is univariate: only wind speed is used as a feature.",
        "The model is specific to this turbine and this dataset.",
        "Wind direction, air density, turbulence, and yaw misalignment are not included.",
        "The dataset has no clear cut-out region, so the curve is treated as constant above "
        "rated speed.",
        "Random K-fold cross-validation ignores temporal dependence; the time-series check "
        "only partly addresses this.",
        "Outlier removal improves the fit but can hide genuine curtailment events; the "
        "dashboard therefore exposes each rule as a toggle and reports its impact.",
    ]:
        bullet(doc, text)


def chapter6(doc):
    chapter(doc, 6, "Advantages, Disadvantages and Applications", "bm_ch6", 10)

    heading(doc, "6.1 Advantages", size=16, before=6, after=6)
    for text in [
        "Physical interpretability: knots at cut-in and rated speed give the model a direct "
        "physical meaning, unlike a black-box regressor.",
        "High accuracy: the hybrid physical spline achieves an R\u00b2 of 0.9935 and an RMSE of "
        "103.89 kW on unseen folds.",
        "Robust cleaning: five explicit rules remove downtime, curtailment, and measurement "
        "errors while retaining genuine low-wind zeros.",
        "Leakage-free evaluation: the spline basis is fitted inside each fold, so the reported "
        "error is honest.",
        "Reproducibility: fixed seeds, pinned library versions, saved metrics, and a training "
        "script make every result repeatable.",
        "Interactivity: the Streamlit dashboard exposes knots, cleaning rules, folds, seed, and "
        "model choice, so the analysis can be explored rather than merely read.",
        "Lightweight deployment: the pipeline runs on a standard laptop without a GPU.",
    ]:
        bullet(doc, text)

    heading(doc, "6.2 Disadvantages and Limitations", size=16, before=12, after=6)
    for text in [
        "Univariate scope: the model ignores wind direction, air density, turbulence, and yaw "
        "misalignment.",
        "Site specificity: the fitted curve is valid for this turbine and this dataset, and "
        "should be refitted for other machines.",
        "Data dependence: the knots are derived from a manufacturer-supplied theoretical curve, "
        "which may not be available for every dataset.",
        "Random CV assumption: shuffled K-fold ignores temporal dependence, and the "
        "TimeSeriesSplit check only partly compensates.",
        "Hidden curtailment: aggressive cleaning can remove genuine de-rated operation, so the "
        "rules must be reviewed for operational use.",
        "No cut-out modelling: the dataset does not contain a clear cut-out region, so the "
        "plateau is treated as constant above rated speed.",
    ]:
        bullet(doc, text)

    heading(doc, "6.3 Applications", size=16, before=12, after=6)
    for text in [
        "Generation forecasting: grid operators can estimate expected power from wind speed and "
        "flag deviations from the normal curve.",
        "Performance monitoring: sustained underperformance against the fitted curve can "
        "trigger maintenance inspection.",
        "Curtailment analysis: comparing measured output with the power curve helps quantify "
        "lost generation.",
        "Turbine benchmarking: the same pipeline can compare turbines across a wind farm.",
        "Teaching and research: the project demonstrates resampling, spline regression, and "
        "diagnostics on a real dataset.",
        "Digital twins: the fitted curve can serve as a baseline component of a turbine digital "
        "twin.",
    ]:
        bullet(doc, text)


def chapter7(doc):
    chapter(doc, 7, "Conclusion and Future Scope", "bm_ch7", 11)

    heading(doc, "7.1 Conclusion", size=16, before=6, after=6)
    para(
        doc,
        "This project set out to model the wind-turbine power curve in a way that respects its "
        "physical structure and estimates its performance honestly. The resulting framework "
        "combines knot detection from the theoretical power curve, five explicit cleaning rules, "
        "eight competing regression models, and leakage-free cross-validation. The hybrid "
        "physical spline is the best model, with a cross-validated RMSE of 103.89 kW, an MAE of "
        "63.38 kW, and an R\u00b2 of 0.9935.",
        size=12, line=1.5, after=8,
    )
    para(
        doc,
        "The comparison with linear regression is the clearest result. A straight line produces "
        "an RMSE of 313.63 kW because it cannot represent the cut-in region, the steep ramp, and "
        "the rated plateau at the same time. Spline models reduce this error by roughly 67 "
        "percent, and the hybrid physical spline adds a clear physical interpretation on top of "
        "that accuracy. The cleaning analysis shows that removing invalid observations is just "
        "as important: it reduces the error of the best model from 393.87 kW to 103.89 kW.",
        size=12, line=1.5, after=8,
    )
    para(
        doc,
        "The chronological TimeSeriesSplit reproduces the same ranking, which shows that the "
        "conclusion is not an artefact of random shuffling. Diagnostic plots identify the ramp "
        "region as the main source of remaining error, and the regime-wise analysis explains why "
        "the R\u00b2 values in the flat regions should be interpreted with care. The Streamlit "
        "dashboard makes the complete workflow transparent and reproducible.",
        size=12, line=1.5, after=8,
    )
    para(
        doc,
        "In summary, the project demonstrates that a small, interpretable, and reproducible "
        "statistical model can outperform a naive baseline by a wide margin when the model "
        "structure matches the physics of the problem and when the evaluation protocol protects "
        "against leakage. It maps directly to Module 4, Resampling Methods, and supports SDG 7, "
        "Affordable and Clean Energy, by improving the reliability of wind-power analysis.",
        size=12, line=1.5, after=8,
    )

    h = heading(doc, "7.2 Future Scope", size=16, before=8, after=6)
    h.paragraph_format.page_break_before = True
    for text in [
        "Multivariate modelling: add wind direction, air density, turbulence intensity, and yaw "
        "misalignment as features.",
        "Explicit cut-out modelling: represent the shutdown region above the cut-out speed "
        "instead of holding the plateau constant.",
        "Non-parametric benchmarks: compare the spline models with gradient boosting and random "
        "forests.",
        "Blocked cross-validation: use blocked or rolling-origin splits to respect temporal "
        "dependence more fully.",
        "Uncertainty quantification: add bootstrap or conformal prediction intervals to the "
        "power forecasts.",
        "Deployment: package the pipeline as a REST service or a scheduled batch job for "
        "operational monitoring.",
        "Multi-turbine analysis: extend the framework to a wind farm and compare turbines under "
        "a common evaluation protocol.",
    ]:
        bullet(doc, text)


def references(doc):
    h = para(doc, "References", size=16, bold=True,
             align=WD_ALIGN_PARAGRAPH.CENTER, line=1.0, after=12)
    h.paragraph_format.page_break_before = True
    add_bookmark(h, "bm_refs", 12)
    refs = [
        "[1] G. Wahba, Spline Models for Observational Data. Philadelphia, PA, USA: SIAM, 1990.",
        "[2] P. Craven and G. Wahba, \u201cSmoothing noisy data with spline functions,\u201d "
        "Numerische Mathematik, vol. 31, no. 4, pp. 377\u2013403, 1979.",
        "[3] T. Hastie, R. Tibshirani, and J. Friedman, The Elements of Statistical Learning: "
        "Data Mining, Inference, and Prediction, 2nd ed. New York, NY, USA: Springer, 2009.",
        "[4] G. James, D. Witten, T. Hastie, and R. Tibshirani, An Introduction to Statistical "
        "Learning with Applications in R, 2nd ed. New York, NY, USA: Springer, 2021.",
        "[5] C. de Boor, A Practical Guide to Splines, rev. ed. New York, NY, USA: Springer, 2001.",
        "[6] S. N. Wood, Generalized Additive Models: An Introduction with R, 2nd ed. Boca "
        "Raton, FL, USA: CRC Press, 2017.",
        "[7] P. J. Green and B. W. Silverman, Nonparametric Regression and Generalized Linear "
        "Models: A Roughness Penalty Approach. London, U.K.: Chapman & Hall, 1994.",
        "[8] M. Stone, \u201cCross-validatory choice and assessment of statistical predictions,\u201d "
        "Journal of the Royal Statistical Society: Series B, vol. 36, no. 2, pp. 111\u2013147, 1974.",
        "[9] R. Kohavi, \u201cA study of cross-validation and bootstrap for accuracy estimation and "
        "model selection,\u201d in Proc. 14th Int. Joint Conf. Artificial Intelligence (IJCAI), "
        "Montreal, QC, Canada, 1995, pp. 1137\u20131143.",
        "[10] A. Kusiak, H. Zheng, and Z. Song, \u201cOn-line monitoring of power curves,\u201d "
        "Renewable Energy, vol. 34, no. 6, pp. 1487\u20131493, 2009.",
        "[11] M. Lydia, S. S. Kumar, A. I. Selvakumar, and G. E. Prem Kumar, \u201cA comprehensive "
        "review on wind turbine power curve modeling techniques,\u201d Renewable and Sustainable "
        "Energy Reviews, vol. 30, pp. 452\u2013460, 2014.",
        "[12] C. Carrillo, A. F. Obando Monta\u00f1o, J. Cidr\u00e1s, and E. D\u00edaz-Dorado, "
        "\u201cReview of power curve modelling for wind turbines,\u201d Renewable and Sustainable "
        "Energy Reviews, vol. 21, pp. 572\u2013581, 2013.",
        "[13] C. Bergmeir and J. M. Ben\u00edtez, \u201cOn the use of cross-validation for time "
        "series predictor evaluation,\u201d Information Sciences, vol. 191, pp. 192\u2013213, 2012.",
        "[14] R. J. Hyndman and G. Athanasopoulos, Forecasting: Principles and Practice, 3rd ed. "
        "Melbourne, Australia: OTexts, 2021.",
    ]
    for text in refs:
        p = para(doc, text, size=12, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
                 before=0, after=8, line=1.15, left=0.45, first=-0.45)


def main():
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = FONT
    style.font.size = Pt(12)
    rpr = style.element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rfonts.set(qn(attr), FONT)
    style.paragraph_format.space_after = Pt(0)
    style.paragraph_format.line_spacing = 1.5

    section1 = doc.sections[0]
    setup_section(section1, cover=True)
    cover(doc)

    section2 = doc.add_section(WD_SECTION.NEW_PAGE)
    setup_section(section2, cover=False)
    set_page_number_format(section2, "lowerRoman", 1)
    add_body_footer(section2)

    certificate(doc)
    acknowledgement(doc)
    abstract(doc)
    table_of_contents(doc)

    section3 = doc.add_section(WD_SECTION.NEW_PAGE)
    setup_section(section3, cover=False)
    set_page_number_format(section3, "decimal", 1)
    add_body_footer(section3)

    chapter1(doc)
    chapter2(doc)
    chapter3(doc)
    chapter4(doc)
    chapter5(doc)
    chapter6(doc)
    chapter7(doc)
    references(doc)

    props = doc.core_properties
    props.title = "Wind Turbine Power Curve Modelling Using Spline Regression"
    props.author = "Adesh U (1DB23AD002)"
    props.subject = "Statistical ML for DS (BAD702) - Project Report"
    props.keywords = "spline regression, wind turbine, cross-validation, power curve"

    doc.save(str(OUT_DOCX))
    print("saved", OUT_DOCX)


if __name__ == "__main__":
    main()





