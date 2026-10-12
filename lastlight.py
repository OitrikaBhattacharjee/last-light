#!/usr/bin/env python3
"""Last Light: a printable walk card.

Code works out sunset, the turnaround time and the time to be home.
A local open-weight model (Gemma via Ollama) writes the small card text.
Nothing leaves your machine: the model is only reached on loopback.
"""
import argparse
import datetime as dt
import html
import json
import math
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

import puzzle
import photo
import scenery

DEFAULT_MODEL = os.environ.get("LASTLIGHT_MODEL", "gemma3:4b")
DEFAULT_URL = "http://127.0.0.1:11434/api/generate"
LOOPBACK = {"127.0.0.1", "localhost", "::1"}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


# Ignore system/environment proxies and never follow redirects, so a request
# meant for this machine cannot be routed or bounced anywhere else.
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
FALLBACK = {
    "title": "A short walk before dark",
    "look_for": [
        "Something that has changed since last week",
        "The tallest thing you can see and what is growing on it",
        "A sound you cannot see the source of",
    ],
    "small_task": "Pick one spot and look at it for a full minute before walking on.",
}


def sun_times(day, lat, lon, tz):
    """Sunrise and sunset as naive local datetimes (NOAA approximation).
    Returns None when the sun does not rise or set that day."""
    n = day.timetuple().tm_yday
    g = 2 * math.pi / 365 * (n - 1)
    eq = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                   - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    d = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g)
         - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g)
         - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    lr = math.radians(lat)
    c = math.cos(math.radians(90.833)) / (math.cos(lr) * math.cos(d)) - math.tan(lr) * math.tan(d)
    if c < -1 or c > 1:
        return None
    ha = math.degrees(math.acos(c))
    rise = 720 - 4 * (lon + ha) - eq + tz * 60
    sset = 720 - 4 * (lon - ha) - eq + tz * 60
    base = dt.datetime.combine(day, dt.time())
    return base + dt.timedelta(minutes=rise), base + dt.timedelta(minutes=sset)


def climate_band(lat):
    a = abs(lat)
    return "tropical" if a < 23.5 else "temperate" if a < 55 else "far north or south"


def clean_text(s, limit):
    s = "".join(ch for ch in str(s) if ch.isprintable())
    return s.strip()[:limit]


def check_url(url, allow_remote):
    host = urllib.parse.urlparse(url).hostname
    if host not in LOOPBACK and not allow_remote:
        raise ValueError(
            "Refusing to send data to %r. Last Light only talks to a model on this "
            "machine. Pass --allow-remote if you really mean it." % host)


def build_prompt(month, band, minutes, weather, surroundings=""):
    return (
        "You write short field cards for people about to take a walk outdoors. "
        "Reply with JSON only, with exactly these keys: "
        '"title" (at most 8 words), '
        '"look_for" (a list of exactly 3 short strings about things to notice outdoors '
        "at this time of year, general and safe, never asking anyone to touch, taste or pick "
        'plants or animals), "small_task" (one sentence that needs no phone). '
        "Do not claim to identify species. Do not name places. "
        "Make the three things fit the surroundings if they are given. "
        "Context: month %s, climate %s, walk length %d minutes, weather note: %s, surroundings: %s."
        % (month, band, minutes, weather or "none given", surroundings or "none given")
    )


def ask_model(prompt, model, url, timeout=180):
    body = json.dumps({"model": model, "prompt": prompt, "stream": False,
                       "format": "json", "options": {"temperature": 0.7}}).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
       with OPENER.open(req, timeout=timeout) as r:
        return json.loads(r.read().decode())["response"]


def parse_card(raw):
    """Validate model output. Raises ValueError if it does not fit the shape."""
    data = json.loads(raw)
    items = data["look_for"]
    if not isinstance(items, list) or len(items) != 3:
        raise ValueError("look_for must be a list of 3")
    return {
        "title": clean_text(data["title"], 80) or FALLBACK["title"],
        "look_for": [clean_text(i, 140) for i in items],
        "small_task": clean_text(data["small_task"], 200),
    }


def reflect(notes, model, url, journal_path, today):
    """Turn rough after-walk notes into a short private journal entry."""
    prompt = ("You help someone remember a walk. Reply with JSON only, with exactly these keys: "
              '"summary" (two plain sentences in the first person, using only what the notes say) and '
              '"next_time" (one short suggestion for the next walk). Do not invent details. '
              "Notes: " + clean_text(notes, 600))
    data = json.loads(ask_model(prompt, model, url))
    entry = {"date": today.isoformat(), "summary": clean_text(data["summary"], 400),
             "next_time": clean_text(data["next_time"], 200)}
    with open(journal_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def render(card, plan, source, pz=None, bg=None, credit=""):
    e = html.escape
    t = lambda x: x.strftime("%H:%M")
    pz = pz or {"got": 0, "finished": 0}
    quest = ("<p>Quest: do the small task, then run <code>lastlight.py --done</code> when you are home "
             "to collect a puzzle piece. You have %d of %d pieces.</p>" % (pz["got"], puzzle.TOTAL))
    trophy = ""
    if pz["finished"]:
        trophy = ('<div class="trophy">%s<p class="src">Puzzles finished: %d</p></div>'
                  % (puzzle.scene(), pz["finished"]))
    items = "\n".join("<li>%s</li>" % e(i) for i in card["look_for"])
    scene = ""
    if bg:
        scene = '<div class="scene" aria-hidden="true" style="background-image:url(data:%s;base64,%s)"></div>' % bg
    if credit:
        source = source + " " + credit
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s</title>
<style>%(css)s</style></head><body>
%(scene)s
<main class="paper">
<h1>%(title)s</h1>
<div class="times">
<p>Leave at %(now)s. Turn around at %(turn)s. Be home by %(home)s.</p>
<p>Sunset is at %(sunset)s, so you have %(left)d minutes of daylight.</p>
</div>
<h2>Look for</h2>
<ul>
%(items)s
</ul>
<h2>One small task</h2>
<p>%(task)s</p>
%(quest)s
<h2>Notes</h2>
<div class="lines"><div></div><div></div><div></div></div>
%(trophy)s
<p class="src">%(src)s Times are calculated from your coordinates and are an estimate. Take a torch if there is any doubt.</p>
</main>
</body></html>
""" % {"title": e(card["title"]), "now": t(plan["now"]), "turn": t(plan["turn"]),
       "home": t(plan["home"]), "sunset": t(plan["sunset"]), "left": plan["left"],
       "items": items, "task": e(card["small_task"]), "src": e(source),
       "quest": quest, "trophy": trophy, "css": scenery.CSS, "scene": scene}


def make_plan(now, lat, lon, tz, minutes):
    st = sun_times(now.date(), lat, lon, tz)
    if st is None:
        raise SystemExit("No normal sunrise or sunset at this latitude today. Judge the light yourself.")
    sunset = st[1]
    left = int((sunset - now).total_seconds() // 60)
    if left < 30:
        raise SystemExit("Only %d minutes of daylight left. Try again tomorrow." % max(left, 0))
    walk = min(minutes, left - 20)
    return {"now": now, "sunset": sunset, "left": left, "walk": walk,
            "turn": now + dt.timedelta(minutes=walk / 2),
            "home": now + dt.timedelta(minutes=walk)}


def main(argv=None):
    p = argparse.ArgumentParser(description="Make a printable walk card with a local model.")
    p.add_argument("--lat", type=float)
    p.add_argument("--lon", type=float)
    p.add_argument("--minutes", type=int, default=45, help="how long you want to walk (10-240)")
    p.add_argument("--weather", default="", help="a few words, e.g. 'cloudy and cool'")
    p.add_argument("--surroundings", default="", help="a few words, e.g. 'park with old trees'")
    p.add_argument("--done", action="store_true", help="after the walk: collect today's puzzle piece")
    p.add_argument("--puzzle", default="puzzle.json", help="where puzzle progress is kept")
    p.add_argument("--background", help="path to your own JPEG or PNG photo for the card background")
    p.add_argument("--credit", default="", help="photo credit shown in the card footer")
    p.add_argument("--reflect", help="after the walk: your rough notes, saved as a private journal entry")
    p.add_argument("--journal", default="walks.jsonl", help="where --reflect saves entries")
    p.add_argument("--tz", type=float, help="UTC offset in hours; defaults to this computer's")
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--ollama-url", default=DEFAULT_URL)
    p.add_argument("--allow-remote", action="store_true")
    p.add_argument("--now", help="override the clock, ISO format, for testing")
    p.add_argument("--out", default="lastlight-card.html")
    a = p.parse_args(argv)

    if a.done:
        today = dt.datetime.fromisoformat(a.now).date() if a.now else dt.date.today()
        state, status = puzzle.award(puzzle.load(a.puzzle), today)
        puzzle.save(a.puzzle, state)
        if status == "already":
            print("You already collected a piece today. Come back tomorrow.")
        elif status == "complete":
            name = "puzzle-complete-%d.svg" % state["finished"]
            with open(name, "w", encoding="utf-8") as f:
                f.write(puzzle.scene())
            print("Puzzle finished. The picture is saved as %s and now appears on your cards." % name)
        else:
            print("Piece collected: %d of %d. Progress picture saved as puzzle.svg." % (state["got"], puzzle.TOTAL))
        if status != "complete":
            with open("puzzle.svg", "w", encoding="utf-8") as f:
                f.write(puzzle.scene(set(state["order"][:state["got"]])))
        return
    if a.reflect:
        check_url(a.ollama_url, a.allow_remote)
        try:
            entry = reflect(a.reflect, a.model, a.ollama_url, a.journal, dt.date.today())
        except (urllib.error.URLError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            raise SystemExit("Could not write the entry (%s). Is Ollama running?" % type(exc).__name__)
        print("Saved to %s:\n%s\nNext time: %s" % (a.journal, entry["summary"], entry["next_time"]))
        return
    if a.lat is None or a.lon is None:
        p.error("--lat and --lon are required to make a card")
    if not (-90 <= a.lat <= 90 and -180 <= a.lon <= 180):
        p.error("coordinates out of range")
    if not (10 <= a.minutes <= 240):
        p.error("--minutes must be between 10 and 240")
    now = dt.datetime.fromisoformat(a.now) if a.now else dt.datetime.now().replace(second=0, microsecond=0)
    tz = a.tz if a.tz is not None else (dt.datetime.now().astimezone().utcoffset().total_seconds() / 3600)
    check_url(a.ollama_url, a.allow_remote)

    bg = None
    if a.background:
        try:
            bg = photo.load(a.background)
        except (OSError, ValueError) as exc:
            raise SystemExit("Could not use the photo: %s" % exc)
    plan = make_plan(now, a.lat, a.lon, tz, a.minutes)
    prompt = build_prompt(now.strftime("%B"), climate_band(a.lat), plan["walk"], clean_text(a.weather, 80),
                          clean_text(a.surroundings, 80))
    try:
        card = parse_card(ask_model(prompt, a.model, a.ollama_url))
        source = "Card text written by %s, running on this computer." % a.model
    except (urllib.error.URLError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print("Model unavailable or gave a bad answer (%s). Using the built-in card." % type(exc).__name__,
              file=sys.stderr)
        card, source = FALLBACK, "Built-in card. No model was used."

    with open(a.out, "w", encoding="utf-8") as f:
        f.write(render(card, plan, source, puzzle.load(a.puzzle), bg, clean_text(a.credit, 120)))
    print("Wrote %s. Print it and leave the phone at home." % a.out)


if __name__ == "__main__":
    main()
