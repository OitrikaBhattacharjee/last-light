import datetime as dt, json, threading, unittest, tempfile, os
from http.server import BaseHTTPRequestHandler, HTTPServer
import lastlight as L
import puzzle as P
import photo as Ph
import xml.etree.ElementTree as ET

class Fake(BaseHTTPRequestHandler):
    reply = {"title": "Evening <b>walk</b>", "look_for": ["a", "b", "c"], "small_task": "Stand still."}
    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        out = json.dumps({"response": json.dumps(self.reply)}).encode()
        self.send_response(200); self.end_headers(); self.wfile.write(out)
    def log_message(self, *a): pass

class T(unittest.TestCase):
    def test_known_sunsets(self):
        # Reference values from published almanac data, 5 minute tolerance.
        cases = [((51.5074, -0.1278, 0, dt.date(2026, 12, 21)), (15, 53)),
                 ((40.7128, -74.006, -4, dt.date(2026, 6, 21)), (20, 31))]
        for (lat, lon, tz, day), (h, m) in cases:
            _, sset = L.sun_times(day, lat, lon, tz)
            want = dt.datetime.combine(day, dt.time(h, m))
            self.assertLess(abs((sset - want).total_seconds()), 300)

    def test_polar_none(self):
        self.assertIsNone(L.sun_times(dt.date(2026, 6, 21), 80, 0, 0))

    def test_remote_refused(self):
        with self.assertRaises(ValueError):
            L.check_url("http://example.com/api/generate", False)

    def test_bad_shape(self):
        with self.assertRaises(ValueError):
            L.parse_card(json.dumps({"title": "x", "look_for": ["a"], "small_task": "y"}))

    def test_end_to_end_escapes_html(self):
        srv = HTTPServer(("127.0.0.1", 0), Fake)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        out = os.path.join(tempfile.mkdtemp(), "c.html")
        L.main(["--lat", "51.5", "--lon", "-0.12", "--tz", "1", "--now", "2026-10-12T16:00",
                "--ollama-url", "http://127.0.0.1:%d/" % srv.server_port, "--out", out])
        text = open(out).read()
        srv.shutdown()
        self.assertIn("&lt;b&gt;walk", text)
        self.assertNotIn("<b>walk", text)
        self.assertIn("Turn around at", text)

    def test_fallback_when_no_model(self):
        out = os.path.join(tempfile.mkdtemp(), "c.html")
        L.main(["--lat", "51.5", "--lon", "-0.12", "--tz", "1", "--now", "2026-10-12T16:00",
                "--ollama-url", "http://127.0.0.1:9/", "--out", out])
        self.assertIn("No model was used", open(out).read())

    def test_too_late(self):
        with self.assertRaises(SystemExit):
            L.make_plan(dt.datetime(2026, 10, 12, 17, 50), 51.5, -0.12, 1, 45)

class R(unittest.TestCase):
    def test_reflect_saves_entry(self):
        class FakeReflect(Fake):
            reply = {"summary": "I walked.", "next_time": "Go earlier."}
        srv = HTTPServer(("127.0.0.1", 0), FakeReflect)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        path = os.path.join(tempfile.mkdtemp(), "w.jsonl")
        L.main(["--reflect", "saw a heron", "--journal", path,
                "--ollama-url", "http://127.0.0.1:%d/" % srv.server_port])
        srv.shutdown()
        self.assertEqual(json.loads(open(path).read())["next_time"], "Go earlier.")

    def test_card_needs_coordinates(self):
        with self.assertRaises(SystemExit):
            L.main(["--minutes", "30"])

    def test_surroundings_in_prompt(self):
        self.assertIn("old trees", L.build_prompt("October", "temperate", 40, "", "old trees"))

class Q(unittest.TestCase):
    def test_one_piece_per_day(self):
        d, s1 = P.award(P.fresh(), dt.date(2026, 10, 12))
        d, s2 = P.award(d, dt.date(2026, 10, 12))
        d, s3 = P.award(d, dt.date(2026, 10, 13))
        self.assertEqual((s1, s2, s3, d["got"]), ("piece", "already", "piece", 2))

    def test_complete_resets_and_counts(self):
        d = P.fresh()
        for i in range(P.TOTAL):
            d, status = P.award(d, dt.date(2026, 11, 1) + dt.timedelta(days=i))
        self.assertEqual((status, d["got"], d["finished"]), ("complete", 0, 1))

    def test_damaged_file_starts_fresh(self):
        path = os.path.join(tempfile.mkdtemp(), "p.json")
        open(path, "w").write('{"order": [1,1], "got": 99}')
        self.assertEqual(P.load(path)["got"], 0)

    def test_svg_is_valid_xml(self):
        ET.fromstring(P.scene())
        ET.fromstring(P.scene({0, 5, 11}))

    def test_done_command_and_card(self):
        old = os.getcwd(); tmp = tempfile.mkdtemp(); os.chdir(tmp)
        try:
            L.main(["--done", "--now", "2026-10-12T10:00"])
            L.main(["--done", "--now", "2026-10-12T11:00"])
            self.assertEqual(P.load("puzzle.json")["got"], 1)
            self.assertTrue(os.path.exists("puzzle.svg"))
            L.main(["--lat", "51.5", "--lon", "-0.12", "--tz", "1", "--now", "2026-10-13T16:00",
                    "--ollama-url", "http://127.0.0.1:9/", "--out", "c.html"])
            self.assertIn("You have 1 of 12 pieces", open("c.html").read())
        finally:
            os.chdir(old)

class V(unittest.TestCase):
    JPEG = (b"\xff\xd8" + b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
            + b"\xff\xe1\x00\x0dExif\x00\x00GPS!!" + b"\xff\xda\x00\x02" + b"pixels" + b"\xff\xd9")

    def png(self):
        def chunk(kind, body):
            return len(body).to_bytes(4, "big") + kind + body + b"\x00\x00\x00\x00"
        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", b"x" * 13) + chunk(b"tEXt", b"secret")
                + chunk(b"IDAT", b"data") + chunk(b"IEND", b""))

    def test_jpeg_strips_gps_keeps_image(self):
        out = Ph.strip_jpeg(self.JPEG)
        self.assertNotIn(b"GPS", out)
        self.assertIn(b"JFIF", out)
        self.assertTrue(out.endswith(b"pixels\xff\xd9"))

    def test_png_strips_text_chunks(self):
        out = Ph.strip_png(self.png())
        self.assertNotIn(b"secret", out)
        self.assertIn(b"IDAT", out)
        
    def test_jpeg_drops_trailing_data_and_other_app_segments(self):
        data = (b"\xff\xd8" + b"\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
                + b"\xff\xe3\x00\x08SECRET" + b"\xff\xda\x00\x02pixels\xff\xd9"
                + b"ftypmp4GPSTRAILER")
        out = Ph.strip_jpeg(data)
        self.assertNotIn(b"SECRET", out)
        self.assertNotIn(b"ftyp", out)
        self.assertNotIn(b"GPS", out)
        self.assertTrue(out.endswith(b"pixels\xff\xd9"))
        
    def test_rejects_non_images_and_big_files(self):
        d = tempfile.mkdtemp()
        bad = os.path.join(d, "x.jpg"); open(bad, "wb").write(b"hello")
        with self.assertRaises(ValueError):
            Ph.load(bad)
        big = os.path.join(d, "big.jpg"); open(big, "wb").write(b"\xff\xd8" + b"0" * (Ph.MAX_BYTES + 1))
        with self.assertRaises(ValueError):
            Ph.load(big)

    def test_card_with_photo_is_clean_and_credited(self):
        import base64, re
        d = tempfile.mkdtemp()
        img = os.path.join(d, "lake.jpg"); open(img, "wb").write(self.JPEG)
        out = os.path.join(d, "c.html")
        L.main(["--lat", "51.5", "--lon", "-0.12", "--tz", "1", "--now", "2026-10-12T16:00",
                "--ollama-url", "http://127.0.0.1:9/", "--out", out,
                "--background", img, "--credit", "Photo: <me>"])
        with open(out, encoding="utf-8") as f:
            text = f.read()
        uri = re.search(r"base64,([A-Za-z0-9+/=]+)", text).group(1)
        self.assertNotIn(b"GPS", base64.b64decode(uri))
        self.assertIn("Photo: &lt;me&gt;", text)

    def test_no_photo_means_no_scene(self):
        out = os.path.join(tempfile.mkdtemp(), "c.html")
        L.main(["--lat", "51.5", "--lon", "-0.12", "--tz", "1", "--now", "2026-10-12T16:00",
                "--ollama-url", "http://127.0.0.1:9/", "--out", out])
        with open(out, encoding="utf-8") as f:
            self.assertNotIn('class="scene"', f.read())

if __name__ == "__main__":
    unittest.main()
