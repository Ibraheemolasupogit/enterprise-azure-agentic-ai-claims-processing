"""Small fixed-layout ASCII PDF and schematic PNG encoders; standard library only."""

import struct
import zlib

from claims_ai.dataset.schema import SourceDocument


def pdf_literal(text: str) -> bytes:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)").encode("ascii")


def render_pdf(source: SourceDocument) -> bytes:
    source = SourceDocument.model_validate(source)
    commands = [
        b"0.08 0.16 0.24 rg 0 776 595 66 re f",
        b"BT /F2 12 Tf 1 1 1 rg 36 810 Td (" + pdf_literal(source.title) + b") Tj ET",
        b"BT /F1 9 Tf 0.08 0.12 0.18 rg 36 750 Td 15 TL",
    ]
    for index, line in enumerate(source.lines):
        commands.append((b"T* " if index else b"") + b"(" + pdf_literal(line) + b") Tj")
    commands.extend(
        [b"ET", b"BT /F1 8 Tf 36 30 Td (SYNTHETIC FIXTURE | NOT POLICY APPROVAL | 1 / 1) Tj ET"]
    )
    stream = b"\n".join(commands) + b"\n"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier-Bold >>",
        f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"endstream",
    ]
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        output.extend(f"{offset:010} 00000 n \n".encode())
    output.extend(
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    )
    return bytes(output)


_FONT = {
    "A": (14, 17, 17, 31, 17, 17, 17),
    "B": (30, 17, 17, 30, 17, 17, 30),
    "C": (14, 17, 16, 16, 16, 17, 14),
    "D": (30, 17, 17, 17, 17, 17, 30),
    "E": (31, 16, 16, 30, 16, 16, 31),
    "F": (31, 16, 16, 30, 16, 16, 16),
    "G": (14, 17, 16, 23, 17, 17, 15),
    "H": (17, 17, 17, 31, 17, 17, 17),
    "I": (31, 4, 4, 4, 4, 4, 31),
    "J": (7, 2, 2, 2, 18, 18, 12),
    "K": (17, 18, 20, 24, 20, 18, 17),
    "L": (16, 16, 16, 16, 16, 16, 31),
    "M": (17, 27, 21, 21, 17, 17, 17),
    "N": (17, 25, 21, 19, 17, 17, 17),
    "O": (14, 17, 17, 17, 17, 17, 14),
    "P": (30, 17, 17, 30, 16, 16, 16),
    "Q": (14, 17, 17, 17, 21, 18, 13),
    "R": (30, 17, 17, 30, 20, 18, 17),
    "S": (15, 16, 16, 14, 1, 1, 30),
    "T": (31, 4, 4, 4, 4, 4, 4),
    "U": (17, 17, 17, 17, 17, 17, 14),
    "V": (17, 17, 17, 17, 17, 10, 4),
    "W": (17, 17, 17, 21, 21, 21, 10),
    "X": (17, 17, 10, 4, 10, 17, 17),
    "Y": (17, 17, 10, 4, 4, 4, 4),
    "Z": (31, 1, 2, 4, 8, 16, 31),
    " ": (0, 0, 0, 0, 0, 0, 0),
}


def render_png(source: SourceDocument) -> bytes:
    source = SourceDocument.model_validate(source)
    label = (
        next(
            line.split(": ", 1)[1] for line in source.lines if line.startswith("damage_location: ")
        )
        .lower()
        .replace(" ", "_")
    )
    if label not in {"front_bumper", "side_door", "rear_bumper"}:
        raise ValueError("unknown schematic label")
    width, height = 480, 200
    pixels = bytearray(width * height)

    def rect(x: int, y: int, w: int, h: int, color: int) -> None:
        for row in range(y, y + h):
            pixels[row * width + x : row * width + x + w] = bytes([color]) * w

    def text(value: str, x: int, y: int) -> None:
        for char in value:
            for row, bits in enumerate(_FONT[char]):
                for column in range(5):
                    if bits & (1 << (4 - column)):
                        rect(x + column * 2, y + row * 2, 2, 2, 1)
            x += 12

    text("SYNTHETIC SCHEMATIC NOT PHOTO", 36, 14)
    rect(100, 68, 280, 70, 2)
    rect(160, 48, 150, 20, 2)
    rect(175, 53, 120, 10, 0)
    rect(135, 128, 35, 25, 1)
    rect(310, 128, 35, 25, 1)
    if label == "front_bumper":
        rect(360, 83, 20, 35, 3)
    elif label == "rear_bumper":
        rect(100, 83, 20, 35, 3)
    else:
        rect(205, 78, 50, 40, 3)
    text("REAR", 45, 95)
    text("FRONT", 390, 95)
    text(label.replace("_", " ").upper(), 120, 173)

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        )

    rows = b"".join(b"\x00" + pixels[row * width : (row + 1) * width] for row in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 3, 0, 0, 0))
        + chunk(b"PLTE", bytes([248, 250, 252, 20, 35, 50, 155, 175, 195, 230, 100, 30]))
        + chunk(b"tEXt", b"Description\x00SYNTHETIC SCHEMATIC NOT A PHOTOGRAPH")
        + chunk(b"IDAT", zlib.compress(rows, level=9))
        + chunk(b"IEND", b"")
    )


def render_document(source: SourceDocument) -> bytes:
    return render_pdf(source) if source.rendering == "pdf-text" else render_png(source)
