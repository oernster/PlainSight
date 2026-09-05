"""Builds real PDFs for the PDF reader's tests.

Real files rather than stand-ins, because what is being tested is what comes
back out of a PDF; a fake that returned text on demand would be testing
the fake. pypdf can write pages but not text onto them, so a small PDF is
assembled here by hand: a catalogue, a page tree, one content stream per page
drawing lines in a standard font, then a cross reference table whose offsets
are computed rather than guessed.
"""

from __future__ import annotations

import io

from pypdf import PdfReader, PdfWriter

HEADER = b"%PDF-1.4\n"
FIRST_LINE_AT = "20 700 Td 14 TL"
FONT_SIZE = "12"
PAGE_BOX = "[0 0 612 792]"
FREE_ENTRY = b"0000000000 65535 f \n"


def _ascii(value: object) -> bytes:
    return str(value).encode("ascii")


def a_pdf(pages: list[list[str]]) -> bytes:
    """A PDF holding these lines of text, one list of lines per page."""
    objects: list[bytes] = []

    def add(body: bytes) -> int:
        objects.append(body)
        return len(objects)

    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    contents: list[int] = []
    for lines in pages:
        drawn = b"BT /F1 " + _ascii(FONT_SIZE) + b" Tf " + _ascii(FIRST_LINE_AT) + b"\n"
        for line in lines:
            drawn += b"(" + line.encode("ascii") + b") Tj T*\n"
        drawn += b"ET"
        contents.append(
            add(
                b"<< /Length "
                + _ascii(len(drawn))
                + b" >>\nstream\n"
                + drawn
                + b"\nendstream"
            )
        )

    # The pages object is numbered before it is written, because each page has
    # to name its parent and the parent has to name every page.
    pages_id = len(objects) + len(pages) + 1
    page_ids = [
        add(
            b"<< /Type /Page /Parent "
            + _ascii(pages_id)
            + b" 0 R /MediaBox "
            + _ascii(PAGE_BOX)
            + b" /Contents "
            + _ascii(content)
            + b" 0 R /Resources << /Font << /F1 "
            + _ascii(font)
            + b" 0 R >> >> >>"
        )
        for content in contents
    ]
    kids = b" ".join(_ascii(one) + b" 0 R" for one in page_ids)
    written_pages_id = add(
        b"<< /Type /Pages /Kids ["
        + kids
        + b"] /Count "
        + _ascii(len(page_ids))
        + b" >>"
    )
    assert written_pages_id == pages_id, "the page tree was numbered wrongly"
    catalog = add(b"<< /Type /Catalog /Pages " + _ascii(pages_id) + b" 0 R >>")

    out = bytearray(HEADER)
    offsets: list[int] = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += _ascii(number) + b" 0 obj\n" + body + b"\nendobj\n"

    started_at = len(out)
    out += b"xref\n0 " + _ascii(len(objects) + 1) + b"\n" + FREE_ENTRY
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode("ascii")
    out += (
        b"trailer\n<< /Size "
        + _ascii(len(objects) + 1)
        + b" /Root "
        + _ascii(catalog)
        + b" 0 R >>\nstartxref\n"
        + _ascii(started_at)
        + b"\n%%EOF\n"
    )
    return bytes(out)


def a_locked_pdf(password: str = "secret") -> bytes:
    """A real PDF encrypted with a password nobody is going to supply."""
    writer = PdfWriter()
    for page in PdfReader(io.BytesIO(a_pdf([["Secret text"]]))).pages:
        writer.add_page(page)
    writer.encrypt(password)
    written = io.BytesIO()
    writer.write(written)
    return written.getvalue()


def a_pdf_with_no_text() -> bytes:
    """A real PDF whose page carries no text, as a scan of one would not."""
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    written = io.BytesIO()
    writer.write(written)
    return written.getvalue()
