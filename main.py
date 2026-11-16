#!/usr/bin/env python3
"""ai-excited-01 entrypoint (Python 3.13, standard library only).

Writes the entry image to the grader's output directory as entry.png.

The image lives beside this file as entry.png: a bioluminescent humpback
whale leaping diagonally across a night sky, trailing glowing plankton
light. The judge sees exactly the bytes copied, so this program does a
plain byte-for-byte copy and nothing else: no resize, no re-encode,
no metadata changes. That keeps the output deterministic: every run
produces byte-identical output.

Usage:
    python3 main.py
    MAKEFUN_OUTPUT_DIR=out python3 main.py   # outside the grader's container

The gate accepts a whole PNG or JPEG of at most 1 MiB and 1024x1024
pixels, so the program checks the copied file's magic bytes, size and
dimensions before it reports success.
"""

import hashlib
import os
import shutil
import struct
import sys
from pathlib import Path

MAX_BYTES = 1_048_576
MAX_SIDE = 1024

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "entry.png"


def png_dimensions(data: bytes) -> tuple[int, int]:
    """Read width and height out of a PNG's IHDR chunk."""
    if len(data) < 33 or data[12:16] != b"IHDR":
        raise ValueError("not a readable PNG")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def jpeg_dimensions(data: bytes) -> tuple[int, int]:
    """Scan a JPEG's markers for the first frame header (SOF0-SOF15)."""
    pos = 2
    while pos + 9 < len(data):
        if data[pos] != 0xFF:
            pos += 1
            continue
        marker = data[pos + 1]
        if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
            pos += 2
            continue
        size = struct.unpack(">H", data[pos + 2:pos + 4])[0]
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            height, width = struct.unpack(">HH", data[pos + 5:pos + 9])
            return width, height
        pos += 2 + size
    raise ValueError("no JPEG frame header found")


def describe(data: bytes) -> tuple[str, int, int]:
    """Return (format, width, height) for a PNG or JPEG byte string."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        width, height = png_dimensions(data)
        return "PNG", width, height
    if data[:2] == b"\xff\xd8":
        width, height = jpeg_dimensions(data)
        return "JPEG", width, height
    raise ValueError("entry.png is neither PNG nor JPEG")


def main() -> int:
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    target = out_dir / "entry.png"

    if not SOURCE.is_file():
        print(f"error: {SOURCE} not found", file=sys.stderr)
        return 1

    data = SOURCE.read_bytes()
    fmt, width, height = describe(data)

    if len(data) > MAX_BYTES:
        print(f"error: image is {len(data)} bytes, over the 1 MiB gate",
              file=sys.stderr)
        return 1
    if width > MAX_SIDE or height > MAX_SIDE:
        print(f"error: image is {width}x{height}, over the 1024x1024 gate",
              file=sys.stderr)
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SOURCE, target)
    written = target.read_bytes()
    if written != data:
        print("error: copied output differs from the source", file=sys.stderr)
        return 1

    digest = hashlib.sha256(data).hexdigest()
    print(f"wrote {target} ({fmt} {width}x{height}, {len(data)} bytes, "
          f"sha256 {digest})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
