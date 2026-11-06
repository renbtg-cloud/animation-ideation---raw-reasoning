#!/usr/bin/env python3
"""Build the complete Brazilian Portuguese edition from README-ptBR.md.

Dependencies: markdown-it-py, weasyprint, pypdf.
Preserves the first illustrated cover page from the repository PDF.
"""
from __future__ import annotations

import io
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from cover_footer import localized_illustrated_cover

from markdown_it import MarkdownIt
from weasyprint import HTML

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "README-ptBR.md"
TARGET = ROOT / "README-ptBR.pdf"

source = SOURCE.read_text(encoding="utf-8")
if source.startswith("# RAW REASONING\n"):
    source = source.split("\n", 1)[1]
parser = MarkdownIt("commonmark", {"html": False, "linkify": True}).enable("table")
body = parser.render(source)
style = r"""
@page {
  size: A4;
  margin: 20mm 19mm 22mm 19mm;
  @bottom-left { content: "RAW REASONING  /  DOSSIÊ DE FICÇÃO ORIGINAL"; font: 8pt "DejaVu Sans", sans-serif; color: #77818e; }
  @bottom-right { content: counter(page); font: 8pt "DejaVu Sans", sans-serif; color: #77818e; }
}
html { font-family: "DejaVu Sans", "Liberation Sans", sans-serif; font-size: 9.4pt; }
body { margin: 0; color: #28313b; line-height: 1.49; }
.cover {
  page-break-after: always;
  color: #f5f2ea;
  padding: 37mm 7mm 9mm 7mm;
}
.cover .eyebrow { color: #caa66a; text-transform: uppercase; letter-spacing: 2.5px; font-size: 10pt; }
.cover h1 { color: #fff; font-size: 45pt; line-height: 1.07; margin: 24mm 0 10mm 0; letter-spacing: 0.8px; }
.cover h2 { color: #d8d0c1; font-size: 16.8pt; font-weight: normal; line-height: 1.45; margin-bottom: 11mm; border: none; }
.cover .rule { width: 32mm; height: 1mm; background: #cca566; margin-bottom: 13mm; }
.cover p { max-width: 124mm; font-size: 11pt; color: #bbc2c8; }
.cover .identity { margin-top: 43mm; color: #cba86d; font-size: 9pt; letter-spacing: 1.3px; }
h2, h3, h4 { font-family: "DejaVu Sans", sans-serif; line-height: 1.27; color: #1d334a; break-after: avoid; }
h2 { font-size: 15.5pt; margin: 9mm 0 4mm; border-bottom: 0.4pt solid #d1d9df; padding-bottom: 2mm; }
h3 { font-size: 11.4pt; margin: 6mm 0 2.5mm; }
h4 { font-size: 10pt; margin: 4.5mm 0 2mm; }
p { margin: 0 0 3.4mm; text-align: left; overflow-wrap: anywhere; }
strong { color: #172c41; }
em { font-style: italic; }
a { color: #145785; text-decoration: underline; overflow-wrap: anywhere; }
a:after { content: none; }
blockquote { margin: 3mm 0 5mm 0; padding: 2.5mm 0 2.5mm 5mm; border-left: 2pt solid #cba668; color: #465361; }
blockquote p:last-child { margin-bottom: 0; }
ul, ol { margin: 2mm 0 4mm; padding-left: 7mm; }
li { margin-bottom: 1.1mm; }
li p { margin-bottom: 1.4mm; }
hr { border: 0; height: .4pt; background: #dce2e7; margin: 6mm 0; }
table { border-collapse: collapse; width: 100%; font-size: 8.6pt; }
th, td { padding: 2.5mm; border-bottom: 0.5pt solid #dbe1e4; text-align: left; overflow-wrap: anywhere; }
th { background: #f1f5f6; }
pre, code { white-space: pre-wrap; overflow-wrap: anywhere; font-family: "DejaVu Sans Mono", monospace; font-size: 8.8pt; }
pre { padding: 3mm; background: #f2f4f6; }
"""
cover = """
<section class="cover">
 <div class="eyebrow">Cambrian Radiation Computing · Original fiction</div>
 <h1>RAW<br/>REASONING</h1>
 <div class="rule"></div>
 <h2>Uma ópera audiovisual de animação<br/>Uma história de amor e uma visão de mundo</h2>
 <p>Love, moral error, embodied artificial minds, mathematical wonder,
 contradiction, freedom and responsibility.</p>
 <p class="identity">DOSSIÊ DE CONCEPÇÃO CRIATIVA · EM DESENVOLVIMENTO</p>
</section>
"""
# Render all current narrative text from Markdown, excluding the original cover.
# The first page of the earlier illustrated edition is retained as an artwork
# source, while all subsequent pages are regenerated from the canonical README.
body_doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>RAW REASONING — Creative Concept Dossier</title>
<style>{style}</style></head><body><main>{body}</main></body></html>"""
body_pdf = HTML(string=body_doc, base_url=ROOT.as_uri() + "/").write_pdf()

writer = PdfWriter()
cover_source = ROOT / "README.pdf"
if cover_source.exists():
    writer.append(io.BytesIO(localized_illustrated_cover(
        cover_source, "UMA OBRA DE FICÇÃO ORIGINAL")))

if not writer.pages:
    fallback_style = style + """
@page:first { background: #141e2b; }
"""
    cover_doc = f"""<!doctype html><html><head><meta charset="utf-8"><style>{fallback_style}</style>
</head><body>{cover}</body></html>"""
    cover_pdf = HTML(string=cover_doc, base_url=ROOT.as_uri() + "/").write_pdf()
    writer.append(io.BytesIO(cover_pdf))

writer.append(io.BytesIO(body_pdf))
writer.add_metadata({
    "/Title": "RAW REASONING — Dossiê de concepção criativa — pt-BR",
    "/Subject": "Dossiê ficcional em português brasileiro; sincronizado ao README-ptBR.md",
})
output = io.BytesIO()
writer.write(output)
TARGET.write_bytes(output.getvalue())

if not TARGET.exists() or TARGET.stat().st_size < 20000:
    raise RuntimeError("PDF generation failed or produced a suspiciously small file")

# Validate that the generated edition contains the newest key story details.
recheck = PdfReader(str(TARGET))
all_text = "\\n".join(page.extract_text() or "" for page in recheck.pages[1:])
for required in ("Winston", "Julia", "datacenters de GPUs", "Everybody Needs Somebody to Love"):
    if required not in all_text:
        raise RuntimeError(f"Generated PDF is missing required story text: {required}")
print(f"Wrote {TARGET.name}: {TARGET.stat().st_size} bytes, {len(recheck.pages)} pages")
