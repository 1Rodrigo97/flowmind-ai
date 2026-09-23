"""Minimal text-PDF generator for tests (no external PDF-writing dependency).

Builds a valid single-page PDF with an extractable text string so pypdf can read
it back. Only ASCII text is supported, which is all the tests need.
"""
from __future__ import annotations


def make_text_pdf(text: str) -> bytes:
    safe = text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        None,  # content stream, filled below
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    stream = f"BT /F1 24 Tf 72 700 Td ({safe}) Tj ET".encode("latin-1")
    objects[3] = b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream)

    out = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (i, body)

    xref_pos = len(out)
    n = len(objects) + 1
    out += b"xref\n0 %d\n" % n
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF" % (n, xref_pos)
    return bytes(out)
