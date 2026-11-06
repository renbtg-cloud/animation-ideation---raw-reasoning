#!/usr/bin/env python3
"""Reuse the concept-art cover, redacting the discarded subtitle.

The former "fictionalized autobiography" footer must not survive either as
visible lettering or as searchable PDF text in a published edition.
"""
from __future__ import annotations

from pathlib import Path
import fitz

NAVY = (22 / 255, 33 / 255, 45 / 255)
GOLD = (0.78, 0.69, 0.53)
FOOTER_RECT = fitz.Rect(390, 810, 571, 834)

def localized_illustrated_cover(source_pdf: Path, label: str) -> bytes:
    with fitz.open(str(source_pdf)) as document:
        page = document[0]
        # Redaction removes the obsolete searchable text while preserving
        # the illustrated image beneath the dark footer band.
        page.add_redact_annot(FOOTER_RECT, fill=NAVY)
        page.apply_redactions(images=0, graphics=0, text=0)
        font_path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
        if font_path.exists():
            font = fitz.Font(fontfile=str(font_path))
            page.insert_font(fontname="CoverFooter", fontfile=str(font_path))
            size = 6.0
            text_width = font.text_length(label, fontsize=size)
            page.insert_text((558 - text_width, 823.5), label,
                             fontname="CoverFooter", fontsize=size, color=GOLD)
        else:
            label_ascii = label.encode("ascii", errors="ignore").decode("ascii")
            text_width = fitz.get_text_length(label_ascii, fontname="helv", fontsize=6)
            page.insert_text((558 - text_width, 823.5), label_ascii,
                             fontname="helv", fontsize=6, color=GOLD)
        return document.convert_to_pdf(from_page=0, to_page=0)
