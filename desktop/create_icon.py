"""Create a clean, code-drawn macOS app icon without external image tools."""

import struct
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parent / "assets"
SIZE = 1024


def inside_polygon(x, y, points):
    inside = False
    previous = points[-1]
    for current in points:
        x1, y1 = previous
        x2, y2 = current
        if (y1 > y) != (y2 > y):
            crossing = (x2 - x1) * (y - y1) / (y2 - y1) + x1
            if x < crossing:
                inside = not inside
        previous = current
    return inside


def chunk(kind, data):
    body = kind + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def png(size):
    shield = [(512, 132), (784, 236), (752, 566), (655, 716), (512, 824), (369, 716), (272, 566), (240, 236)]
    check = [(396, 486), (449, 539), (628, 360), (675, 407), (449, 633), (349, 533)]
    scale = SIZE / size
    rows = bytearray()
    for py in range(size):
        rows.append(0)
        for px in range(size):
            x, y = (px + 0.5) * scale, (py + 0.5) * scale
            # Blue rounded-square app tile, evaluated with a rounded-rectangle distance.
            cx = max(208, min(816, x))
            cy = max(208, min(816, y))
            tile = (x - cx) ** 2 + (y - cy) ** 2 <= 112 ** 2
            if not tile:
                color = (0, 0, 0, 0)
            elif inside_polygon(x, y, shield):
                color = (58, 101, 188, 255) if inside_polygon(x, y, check) else (255, 255, 255, 255)
            else:
                color = (58, 101, 188, 255)
            rows.extend(color)
    header = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(bytes(rows), 9)) + chunk(b"IEND", b"")


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "icon.png").write_bytes(png(1024))


if __name__ == "__main__":
    main()
