"""Load a background photo for the card and strip private metadata (EXIF, GPS, text chunks).
JPEG and PNG only. Pure standard library."""
import base64
import os

MAX_BYTES = 5 * 1024 * 1024
PNG_SIG = b"\x89PNG\r\n\x1a\n"
PNG_DROP = {b"eXIf", b"tEXt", b"iTXt", b"zTXt", b"tIME"}


def keep_segment(marker, seg):
    """Allowlist: keep only the metadata a browser needs to draw the picture."""
    if 0xE0 <= marker <= 0xEF:  # APPn segments carry EXIF, XMP, MPF, vendor data
        if marker == 0xE0 and seg[4:9] == b"JFIF\x00":
            return True
        if marker == 0xE2 and seg[4:16] == b"ICC_PROFILE\x00":
            return True
        if marker == 0xEE and seg[4:9] == b"Adobe":
            return True
        return False
    if marker == 0xFE:  # comments
        return False
    return True


def strip_jpeg(data):
    if data[:2] != b"\xff\xd8":
        raise ValueError("not a JPEG")
    out, i, size = bytearray(b"\xff\xd8"), 2, len(data)
    while i + 1 < size:
        if data[i] != 0xFF:
            raise ValueError("damaged JPEG")
        m = data[i + 1]
        if m == 0xFF:  # fill byte
            i += 1
            continue
        if m == 0xD9:  # end of image: drop anything after it
            out += b"\xff\xd9"
            return bytes(out)
        if m == 0x01 or 0xD0 <= m <= 0xD7:  # markers with no length
            out += data[i:i + 2]
            i += 2
            continue
        if i + 4 > size:
            raise ValueError("damaged JPEG")
        n = int.from_bytes(data[i + 2:i + 4], "big")
        if n < 2 or i + 2 + n > size:
            raise ValueError("damaged JPEG")
        if m == 0xDA:  # scan: copy header + image data up to the next real marker
            j = i + 2 + n
            while True:
                j = data.find(b"\xff", j)
                if j == -1 or j + 1 >= size:
                    raise ValueError("damaged JPEG")
                nxt = data[j + 1]
                if nxt == 0x00 or 0xD0 <= nxt <= 0xD7:
                    j += 2
                elif nxt == 0xFF:
                    j += 1
                else:
                    break
            out += data[i:j]
            i = j
            continue
        seg = data[i:i + 2 + n]
        if keep_segment(m, seg):
            out += seg
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
