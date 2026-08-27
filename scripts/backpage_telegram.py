#!/usr/bin/env python3
"""The decisive test: did the channels stop publishing, or did the mirror stop crediting them?

This is the open question RESEARCH.md calls the study's hinge, and until it is answered the
project's own README says "the supply was interrupted" is the reading the evidence best
supports, not a fact.

WHY IT IS THE HINGE. The Hungarian mirror's output fell 63.7% after the April 2026 election,
and the three Hungarian-language aggregator channels it credits most account for 87% of that
fall. Everything the project holds is the MIRROR'S side of that relationship: CheckFirst's
scrape records what the mirror published and what it credited. Nothing in it can see whether
the channels themselves went quiet. Two very different stories fit the same data:

    the channels stopped posting        -> an upstream supply interruption
    the channels kept posting           -> the mirror stopped crediting them, and the
                                           interruption is a decision on the mirror's side

WHAT THIS DOES. Telegram's public preview at t.me/s/<channel> paginates backwards with
?before=<post_id>. Walking it from today to a cutoff reconstructs the channel's own posting
history, day by day, independent of the mirror. That series is then comparable with the
mirror's credit series for the same channel from data/panel/mirror_source_day/.

WHAT IT COLLECTS, AND WHAT IT DELIBERATELY DOES NOT. Post ids and timestamps only — no text.
The question is a volume question, so the text is not needed, and not collecting it means
this walk cannot become an unfiltered second corpus alongside the archive the smear filter
guards. The archive's sampled specimens remain the only text this project keeps.

WHAT IT CANNOT SHOW, stated here because the answer will be quoted:
  · t.me/s/ renders the channel's public preview. A post deleted before this walk ran is
    invisible to it, so a day's count is a lower bound on what was posted that day, and a
    channel that posted-then-deleted is indistinguishable from one that never posted.
  · Media-only posts with no text still appear in the preview and are counted; the mirror
    could not have laundered them as articles. So the channel series is generous to the
    "channels kept posting" reading, which is the direction that makes this test hard to
    pass rather than easy.
  · It shows what the channel published, never why the mirror's credits moved. A mirror
    that keeps crediting a quiet channel and one that stops crediting a busy one are both
    visible here; the reason for either is not.

    python3 scripts/backpage_telegram.py                    # resume or start the walk
    python3 scripts/backpage_telegram.py --since 2026-02-01
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "derived" / "channel_activity.json"
STATE = ROOT / "data" / "derived" / ".backpage_state.json"

UA = ("Mozilla/5.0 (compatible; poisoned-well/1.0; research; "
      "+https://github.com/abognar-git/poisoned-well)")

# The three channels whose collapse accounts for 87% of the mirror's post-election fall.
# derive_diet.py marks them in_collapsed_set; they are named here so this script states its
# own scope rather than inheriting it silently.
CHANNELS = ["oroszokazigazsagoldalan", "ebredes2017", "greatawakeningmagyarok"]
DEFAULT_SINCE = "2026-02-01"
DELAY = 0.7          # polite: this is one deep walk, not a crawl
PAGE_BUDGET = 2000   # per channel, a backstop against an infinite loop


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8", errors="replace")


def page_posts(html):
    """(post_id, iso_timestamp) for every message block on a preview page."""
    out = []
    for block in re.split(r"tgme_widget_message_wrap", html)[1:]:
        pid = re.search(r'data-post="[^"]+/(\d+)"', block)
        tm = re.search(r'datetime="([^"]+)"', block)
        if pid and tm:
            out.append((int(pid.group(1)), tm.group(1)))
    return out


def walk(channel, since, state):
    """Page backwards until the oldest post on a page predates `since`."""
    seen = {int(k): v for k, v in state.get(channel, {}).get("posts", {}).items()}
    before = state.get(channel, {}).get("next_before")
    pages = 0
    while pages < PAGE_BUDGET:
        url = f"https://t.me/s/{channel}" + (f"?before={before}" if before else "")
        posts, err = None, None
        for attempt in range(3):
            try:
                posts = page_posts(fetch(url))
                break
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
                err = e
                time.sleep(3 * (attempt + 1))    # back off; a 429 after 1,000 polite
                                                 # requests ended the first walk silently
        if posts is None:
            print(f"  {channel}: stopped on {type(err).__name__} after {pages} page(s) "
                  f"— resumable from ?before={before}", flush=True)
            break
        if not posts:
            print(f"  {channel}: reached the start of the channel after {pages} page(s)", flush=True)
            before = None
            break
        pages += 1
        for pid, ts in posts:
            seen[pid] = ts
        oldest_id = min(p for p, _ in posts)
        oldest_ts = min(t for _, t in posts)
        before = oldest_id
        if pages % 25 == 0:
            print(f"  {channel}: {pages} pages, {len(seen):,} posts, back to {oldest_ts[:10]}",
                  flush=True)
        if oldest_ts[:10] < since:
            break
        time.sleep(DELAY)

    state[channel] = {"posts": {str(k): v for k, v in seen.items()},
                      "next_before": before,
                      "pages_walked": state.get(channel, {}).get("pages_walked", 0) + pages}
    return seen


def daily(posts, since):
    c = Counter(ts[:10] for ts in posts.values() if ts[:10] >= since)
    return dict(sorted(c.items()))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--since", default=DEFAULT_SINCE, help="walk back to this date")
    ap.add_argument("--channels", nargs="*", default=CHANNELS)
    a = ap.parse_args()

    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    series = {}
    for ch in a.channels:
        print(f"walking {ch} back to {a.since}…")
        posts = walk(ch, a.since, state)
        STATE.write_text(json.dumps(state))          # checkpoint after every channel
        d = daily(posts, a.since)
        ids = sorted(posts)
        series[ch] = {
            "daily_posts": d,
            "days_covered": len(d),
            "posts_in_window": sum(d.values()),
            "first_day": min(d) if d else None,
            "last_day": max(d) if d else None,
            "id_span": [ids[0], ids[-1]] if ids else None,
            "pages_walked": state[ch]["pages_walked"],
            # A channel numbers its posts sequentially, so the ids we hold over the ids the
            # channel issued across the same span is how much of it this walk actually saw.
            # A gap is a post deleted before the walk, or one the preview does not render.
            "id_coverage": round(len(posts) / (ids[-1] - ids[0] + 1), 4) if len(ids) > 1 else None,
        }
        print(f"  {ch}: {series[ch]['posts_in_window']:,} posts across "
              f"{series[ch]['days_covered']} days, id coverage "
              f"{series[ch]['id_coverage']}")

    out = {
        "note": ("The three collapsed channels' own posting history, reconstructed from "
                 "Telegram's public preview independently of the mirror. Post ids and "
                 "timestamps only — no text is collected. A day's count is a LOWER BOUND: "
                 "a post deleted before this walk ran cannot be seen, and media-only posts "
                 "the mirror could not have laundered as articles are counted. Both biases "
                 "favour the 'the channels kept posting' reading, which is the one this "
                 "test would have to overturn."),
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "since": a.since,
        "channels": series,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    print(f"channel_activity.json: {len(series)} channels")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
