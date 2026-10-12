# Last Light

Last Light makes a one page paper card for a walk. Print it, put the phone down, go outside.

Plain code works out sunset, when to turn around and when to be home. A local Gemma model, run through Ollama on your own computer, writes the short part of the card: three things to notice and one small task. Nothing is sent to any server. There are no accounts, no API keys and no tracking.

Made for the Hacktoberfest Open-Source AI Challenge, Week 1 (Touch Grass).

## Run it

You need Python 3.9+ and [Ollama](https://ollama.com). There are no other dependencies.

    ollama pull gemma3:4b
    python3 lastlight.py --lat 12.97 --lon 77.59 --minutes 45 --weather "cloudy and cool"

Open `lastlight-card.html` and print it. Use `--model` to pick any Gemma you have pulled, `--tz` to set the UTC offset if your computer's is wrong, and `--out` to choose the file name.

Tell it where you are going so the card fits: add `--surroundings "park with old trees"`.

After the walk, jot rough notes and save a private journal entry (kept in `walks.jsonl` on your machine):

    python3 lastlight.py --reflect "saw a heron, path was muddy, turned back early"

Each card has a quest: the small task. When you are back, run `python3 lastlight.py --done` to collect one piece of a 12 piece picture (one per day, on the honor system). Progress is saved as `puzzle.svg`. Finish the picture and it appears on your future cards, then a new puzzle starts. Progress lives in `puzzle.json` on your machine.

For a photo background, use your own picture of where you walk: `--background lake.jpg --credit "Photo: your name"`. JPEG or PNG, up to 5 MB (about 1 MB is plenty). The photo is stored inside the card file, nothing is fetched from the internet, and metadata such as GPS location is stripped before embedding. If you use someone else's photo, check its licence and credit it. Photos are not committed to the repo.

If Ollama is not running, you get a plain built-in card and the footer says no model was used.

## Why open weights matter here

- Your coordinates and your habits are about when you are away from home. They stay on your machine.
- It works with no signal. Run it before you leave.
- Swapping the model is one flag. A smaller model runs on an old laptop.
- It costs nothing to run.

## Safety choices

- The tool refuses to send anything to a non-loopback address unless you pass `--allow-remote`.
- Model output is checked for shape and length, then HTML escaped, so a bad answer cannot inject markup.
- Times are computed by code, never by the model. They are estimates, so take a torch if unsure.
- The model is told not to identify species or suggest touching or picking anything.
- Requests to the model ignore system proxy settings and are never redirected, so they cannot be routed off this machine.
- Photos are cleaned with an allowlist: only the data needed to draw the picture is kept, and anything after the end of the image is dropped.

## Tests

    python3 -m unittest -v

The tests start a fake local model server, so they need no model installed.

## Limits

Sunset uses a standard approximation (about a few minutes of error). It does not know about hills or buildings. Small models can give bland suggestions, so the card is a nudge and not a guide.
