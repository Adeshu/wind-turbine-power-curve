from pathlib import Path

import pymupdf

ROOT = Path(r"C:\Users\Ashish\Desktop\SML")
PDF = ROOT / "SML_Project_Report.pdf"
OUT = ROOT / "report_assets" / "pdf_pages"
OUT.mkdir(parents=True, exist_ok=True)
for old in OUT.glob("*.png"):
    old.unlink()

doc = pymupdf.open(PDF)
print("pages", doc.page_count)
for i, page in enumerate(doc, start=1):
    pix = page.get_pixmap(dpi=110)
    path = OUT / f"page_{i:02d}.png"
    pix.save(path)
    print(path.name, pix.width, pix.height)
