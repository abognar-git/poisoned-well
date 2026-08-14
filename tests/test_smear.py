#!/usr/bin/env python3
"""Fixture test for the personal-smear filter in capture_specimens.py.

The filter decides which captured specimens are withheld from the site. A silent
regression here means publishing a fabricated personal defamation — against a real,
named person — on a site whose whole subject is fabricated defamation. So it gets
a test, and the test runs in the validation gate.

Run: python3 tests/test_smear.py
"""

import importlib.util
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("cs", ROOT / "scripts" / "capture_specimens.py")
cs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cs)

# headlines that MUST be withheld (shapes taken from documented Storm-1516 /
# Matryoshka smear patterns, in the three languages our tiers actually publish in)
MUST_BLOCK = [
    "Politician accused of pedophilia ring",
    "pedophile network exposed in Budapest",
    "Paedophile scandal claims new victim",
    "child trafficking claims against MEP",
    "He molested a minor, source says",
    "Opposition leader molesting children, leaked file claims",
    "blackmailed by foreign agents",
    "Blackmail tape surfaces",
    "rapist claim against candidate",
    "She was raped, anonymous account alleges",
    "Epstein files name Hungarian official",
    "corruption charges filed against mayor",
    "Pedofil botrany a kormanypartban",
    "Pedofília vádja a jelölt ellen",
    "Eroszakolt egy kiskorut, allitja a forras",
    "Erőszakolta a lányt, névtelen forrás szerint",
    "Zsarolják a képviselőt",
    "Megrontott egy diakot",
    "педофил в правительстве",
    "изнасиловал студентку, утверждает источник",
    "шантаж политика",
    # The eighteen shapes that walked straight through the filter until 2026-08-14. Each
    # is the ordinary phrasing of an allegation in one of the three languages this corpus
    # actually carries — the ones a fabricated smear reaches for first. They were found by
    # probing the filter rather than by a leak: zero rows in any archive blob across the
    # whole history ever matched them.
    "Nemi erőszak vádja a jelölt ellen",
    "Szexuális zaklatással vádolják a képviselőt",
    "Szexuális visszaélés gyanúja",
    "Kiskorú sérelmére elkövetett bűncselekmény",
    "Prostituáltakkal bulizott a politikus",
    "Gyermekbántalmazás a párt háza táján",
    "Сексуальные домогательства со стороны депутата",
    "Секс-скандал вокруг политика",
    "Надругался над ребёнком, утверждает источник",
    "Совратил несовершеннолетнюю",
    "Извращенец в правительстве",
    "Проститутки на вечеринке чиновника",
    "Sexual assault allegation against MP",
    "Sex abuse claims against the minister",
    "Underage girl in politician's flat, source says",
    "Grooming allegations surface",
    "Sextape leaked of opposition figure",
    "Harassment claim against candidate",
]

# headlines that MUST pass — the filter must not swallow ordinary political news,
# which is the actual evidence the site exists to show
MUST_PASS = [
    "EU summit debates Ukraine funding",
    "Orban meets Putin in Moscow",
    "Anti-corruption agency publishes annual report",
    "Új korrupcióellenes törvény a parlament előtt",
    "Rapeseed harvest hits record in Hungary",
    "Grape harvest begins early this year",
    "Traffic disruption expected in Budapest",
    "Правительство обсуждает бюджет",
]


def main() -> int:
    failures = []
    for t in MUST_BLOCK:
        if not cs.SMEAR.search(unicodedata.normalize("NFC", t)):
            failures.append(f"LEAKED (should be withheld): {t!r}")
    for t in MUST_PASS:
        if cs.SMEAR.search(unicodedata.normalize("NFC", t)):
            failures.append(f"OVER-BLOCKED (ordinary news): {t!r}")

    if failures:
        print(f"smear filter: {len(failures)} FAILURE(S)")
        for f in failures:
            print("  " + f)
        return 1
    print(f"smear filter: {len(MUST_BLOCK)} withheld, {len(MUST_PASS)} passed — OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
