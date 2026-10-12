import re, base64
t = open("lastlight-card.html", encoding="utf-8").read()
b = base64.b64decode(re.search(r"base64,([A-Za-z0-9+/=]+)", t).group(1))
for tag in [b"Exif", b"ftyp", b"xpacket"]:
    print(tag, b.count(tag))
print("ends cleanly:", b[-2:] == b"\xff\xd9")
