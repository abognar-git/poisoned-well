#!/usr/bin/env python3
"""Generate data/derived/globe.json for the 3D hero scene.

  - land   : dot-matrix landmass points (lat, lon) ray-cast against Natural Earth
             110m land polygons (fetched once into data/raw/)
  - mirrors: one point per Pravda-network mirror, at country/region anchor coords
             (prototype-grade centroids, hand-authored below; duplicates jittered)
  - origin : Moscow, the arc source

Coordinates are anchors for visualization, not assertions about server locations —
VIGINUM located hosting on Russian IPs; the anchors show *audience targeting*.
"""

import json
import math
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "derived"

LAND_URL = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
            "master/geojson/ne_110m_land.geojson")

GRID_STEP = 1.1  # degrees; ~13k land dots at this step

# Audience-anchor coordinates per mirror name (domain minus .news-pravda.com).
# Language mirrors anchor to the language's principal country, slightly offset.
ANCHORS = {
    "abkhazia": (43.0, 41.0), "albania": (41.2, 20.1), "algeria": (28.0, 2.6),
    "armenia": (40.3, 45.0), "au": (-25.3, 133.8), "australia": (-27.0, 135.5),
    "austria": (47.6, 14.1), "balkan": (43.9, 20.5), "basque": (43.0, -2.6),
    "belgique": (50.6, 4.7), "belgium": (50.9, 4.2),
    "bosnia-herzegovina": (44.2, 17.8), "bulgaria": (42.8, 25.2),
    "burkina-faso": (12.3, -1.6), "cameroon": (5.7, 12.7), "canada": (56.0, -106.0),
    "car": (6.6, 20.9), "catalan": (41.6, 1.9), "chad": (15.4, 18.7),
    "croatia": (45.5, 15.5), "cyprus": (35.0, 33.2), "czechia": (49.8, 15.5),
    "denmark": (56.0, 9.5), "deutsch": (50.6, 9.8), "dprk": (40.3, 127.2),
    "dutch": (52.6, 5.6), "egypt": (26.7, 30.1), "en-hu": (47.4, 18.6),
    "en-jp": (36.6, 139.1), "en-ro": (45.6, 24.4), "eritrea": (15.2, 39.1),
    "estonia": (58.7, 25.5), "eu": (50.85, 4.35), "finland": (64.5, 26.0),
    "francais": (47.2, 1.7), "france": (46.6, 2.4), "galician": (42.8, -8.0),
    "gambia": (13.4, -15.4), "ge": (42.0, 43.5), "germany": (51.2, 10.4),
    "greece": (39.3, 22.5), "guinea": (10.4, -10.9), "guinea-bissau": (12.0, -14.9),
    "hu-hu": (46.9, 19.5), "hungary": (47.2, 19.4), "iceland": (64.9, -18.6),
    "ireland": (53.2, -8.2), "irish": (53.5, -7.8), "italy": (42.8, 12.8),
    "ja-jp": (35.8, 137.8), "japan": (36.2, 138.2), "korea": (39.0, 126.5),
    "latvia": (56.9, 24.9), "lithuania": (55.2, 23.9), "lt": (55.6, 24.3),
    "luxembourg": (49.8, 6.1), "mali": (17.6, -3.5), "malta": (35.9, 14.4),
    "maori": (-40.9, 175.5), "mauritania": (20.3, -10.3), "md": (47.5, 28.8),
    "moldova": (47.2, 28.4), "montenegro": (42.8, 19.2), "nato": (50.88, 4.42),
    "netherlands": (52.2, 5.3), "new-zealand": (-41.5, 172.8),
    "news-pravda.com": (55.75, 37.62), "niger": (17.6, 8.1), "nigeria": (9.1, 8.7),
    "north-macedonia": (41.6, 21.7), "norway": (61.0, 8.5), "ossetia": (42.3, 44.1),
    "poland": (52.1, 19.4), "portugal": (39.6, -8.0), "portuguese": (38.9, -8.5),
    "rca": (7.0, 21.4), "ro-ro": (46.0, 25.0), "romania": (45.9, 24.9),
    "scotland": (56.5, -4.2), "senegal": (14.5, -14.5), "serbia": (44.2, 20.9),
    "singapore": (1.35, 103.8), "slovakia": (48.7, 19.7), "slovenia": (46.1, 14.8),
    "south-korea": (36.5, 127.9), "south-sudan": (7.3, 30.3), "spain": (40.2, -3.6),
    "spanish": (39.7, -4.1), "srpska": (44.7, 17.3), "sudan": (15.6, 30.2),
    "sweden": (62.2, 14.6), "switzerland": (46.8, 8.2), "syria": (35.0, 38.5),
    "taiwan": (23.8, 121.0), "trump": (38.9, -77.04), "turkey": (39.0, 35.2),
    "ua": (49.0, 31.4), "uk": (54.0, -2.0), "usa": (39.8, -98.6), "wales": (52.3, -3.7),
}

HIGHLIGHT = {"hungary", "hu-hu", "en-hu"}
CEE = {"slovakia", "czechia", "poland", "romania", "ro-ro", "en-ro", "moldova", "md"}


def point_in_ring(lat, lon, ring):
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat):
            x_int = (xj - xi) * (lat - yi) / (yj - yi) + xi
            if lon < x_int:
                inside = not inside
        j = i
    return inside


def build_land():
    cache = RAW / "ne_110m_land.geojson"
    if not cache.exists():
        req = urllib.request.Request(LAND_URL, headers={"User-Agent": "poisoned-well-research"})
        cache.write_bytes(urllib.request.urlopen(req, timeout=120).read())
    gj = json.loads(cache.read_text())

    polys = []  # (bbox, outer_ring) — 110m holes are negligible at this dot pitch
    for feat in gj["features"]:
        geom = feat["geometry"]
        rings = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        for poly in rings:
            outer = poly[0]
            lons = [p[0] for p in outer]
            lats = [p[1] for p in outer]
            polys.append(((min(lons), min(lats), max(lons), max(lats)), outer))

    pts = []
    lat = -60.0  # skip Antarctica for a cleaner editorial globe
    while lat <= 85.0:
        # constant surface density: thin the grid as circles of latitude shrink
        step = GRID_STEP / max(math.cos(math.radians(lat)), 0.25)
        lon = -180.0
        while lon <= 180.0:
            for (x0, y0, x1, y1), ring in polys:
                if x0 <= lon <= x1 and y0 <= lat <= y1 and point_in_ring(lat, lon, ring):
                    pts.append([round(lat, 1), round(lon, 1)])
                    break
            lon += step
        lat += GRID_STEP
    return pts


def build_mirrors():
    domains = json.loads((RAW / "pravda" / "domains.json").read_text())
    summary = json.loads((OUT / "pravda_summary.json").read_text())
    seen: dict[tuple, int] = {}
    mirrors, unmapped = [], []
    for d in domains:
        name = d["domain"].replace(".news-pravda.com", "")
        if name not in ANCHORS:
            unmapped.append(name)
            continue
        lat, lon = ANCHORS[name]
        n = seen.get((lat, lon), 0)  # jitter exact-duplicate anchors
        seen[(lat, lon)] = n + 1
        if n:
            lat, lon = lat + 0.9 * n, lon + 1.4 * n
        stats = summary.get(d["domain"], {})
        mirrors.append({
            "domain": d["domain"],
            "lat": lat, "lon": lon,
            "tier": ("highlight" if name in HIGHLIGHT else
                     "cee" if name in CEE else "base"),
            "total": stats.get("total_articles"),
        })
    return mirrors, unmapped


def main() -> int:
    land = build_land()
    mirrors, unmapped = build_mirrors()
    out = {
        "note": "anchor coords show audience targeting, not server locations",
        "origin": {"name": "Moscow", "lat": 55.75, "lon": 37.62},
        "land": land,
        "mirrors": mirrors,
    }
    OUT.joinpath("globe.json").write_text(json.dumps(out))
    print(f"globe.json: {len(land)} land dots, {len(mirrors)} mirrors "
          f"({len(unmapped)} unmapped: {unmapped})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
