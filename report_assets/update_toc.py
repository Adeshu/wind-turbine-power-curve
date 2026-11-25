import json
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt

ROOT = Path(r"C:\Users\Ashish\Desktop\SML")
DOCX = ROOT / "SML_Project_Report.docx"
PAGES = json.loads((ROOT / "report_assets" / "pages.json").read_text(encoding="utf-8-sig"))

ROMAN = {1: "i", 2: "ii", 3: "iii", 4: "iv", 5: "v"}


def rng(start_key, end_key):
    start = PAGES[start_key]
    end = PAGES[end_key] - 1
    return str(start) if start == end else f"{start}-{end}"


values = {
    1: ROMAN[PAGES["bm_certificate"]],
    2: ROMAN[PAGES["bm_ack"]],
    3: ROMAN[PAGES["bm_abstract"]],
    4: rng("bm_ch1", "bm_ch2"),
    10: rng("bm_ch2", "bm_ch3"),
    11: rng("bm_ch3", "bm_ch4"),
    13: rng("bm_ch4", "bm_ch5"),
    15: rng("bm_ch5", "bm_ch6"),
    16: rng("bm_ch6", "bm_ch7"),
    20: rng("bm_ch7", "bm_refs"),
    21: str(PAGES["bm_refs"]),
}

doc = Document(str(DOCX))
target = None
for table in doc.tables:
    if table.rows and table.rows[0].cells[0].text.strip() == "Chapter No.":
        target = table
        break
if target is None:
    raise SystemExit("TOC table not found")

for row_index, value in values.items():
    cell = target.rows[row_index].cells[2]
    cell.text = ""
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(1)
    run = p.add_run(value)
    run.font.name = "Times New Roman"
    run.font.size = Pt(11.5)
    run.font.bold = row_index in {1, 2, 3, 4, 10, 11, 13, 15, 16, 20, 21}

doc.save(str(DOCX))
print("updated TOC", values)
