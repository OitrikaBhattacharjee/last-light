"""Load a background photo for the card and strip private metadata (EXIF, GPS, text chunks).
JPEG and PNG only. Pure standard library."""
import base64
import os

MAX_BYTES = 5 * 1024 * 1024
PNG_SIG = b"\x89PNG\r\n\x1a\n"
PNG_DROP = {b"eXIf", b"tEXt", b"iTXt", b"zTXt", b"tIME"}


def strip_jpeg(data):
    if data[:2] != b"\xff\xd8":
        raise ValueError("not a JPEG")
    out, i = bytearray(b"\xff\xd8"), 2
    while i < len(data):
        if data[i] != 0xFF:
            raise ValueError("damaged JPEG")
        m = data[i + 1]
        if m == 0xFF:
            i += 1
            continue
        if m == 0xDA:  # start of scan: the rest is image data
            out += data[i:]
            return bytes(out)
        if m == 0x01 or 0xD0 <= m <= 0xD7:
            out += data[i:i + 2]
            i += 2
            continue
        n = int.from_bytes(data[i + 2:i + 4], "big")
        if n < 2 or i + 2 + n > len(data):
            raise ValueError("damaged JPEG")
        if m not in (0xE1, 0xED, 0xFE):  # drop EXIF/XMP, IPTC, comments
            out += data[i:i + 2 + n]
        i += 2 + n
    raise ValueError("damaged JPEG")


def strip_png(data):
    if data[:8] != PNG_SIG:
        raise ValueError("not a PNG")
    out, i = bytearray(PNG_SIG), 8
    while i + 8 <= len(data):
        n = int.from_bytes(data[i:i + 4], "big")
        kind = data[i + 4:i + 8]
        end = i + 12 + n
        if end > len(data):
            raise ValueError("damaged PNG")
        if kind not in PNG_DROP:
            out += data[i:end]
        i = end
        if kind == b"IEND":
            return bytes(out)
    raise ValueError("damaged PNG")


def load(path):
    """Returns (mime, base64 text) of the cleaned image."""
    if os.path.getsize(path) > MAX_BYTES:
        raise ValueError("photo is over 5 MB. Shrink it first (about 1 MB is plenty).")
    with open(path, "rb") as f:
        data = f.read()
    if data[:2] == b"\xff\xd8":
        mime, clean = "image/jpeg", strip_jpeg(data)
    elif data[:8] == PNG_SIG:
        mime, clean = "image/png", strip_png(data)
    else:
        raise ValueError("only JPEG and PNG photos are supported")
    return mime, base64.b64encode(clean).decode("ascii")
