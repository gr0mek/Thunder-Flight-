from datetime import date

from flightwatch.text import NBSP, decimal, duration, long_day, pct, plural, wd_dm, zl, zl_signed


def test_zl_rounds_minor_units_and_groups_thousands() -> None:
    assert zl(1_084_000) == f"10{NBSP}840{NBSP}zł"
    assert zl(1_084_049, sep=" ") == "10 840 zł"
    assert zl(1_084_050, sep=" ") == "10 841 zł"


def test_signed_amounts_use_typographic_minus() -> None:
    assert zl_signed(42_000, sep=" ") == "+420 zł"
    assert zl_signed(-12_000, sep=" ") == "−120 zł"


def test_decimal_and_percent_use_polish_comma() -> None:
    assert decimal(37.9) == "37,9"
    assert decimal(39.0) == "39"
    assert pct(-3.14, signed=True) == "−3,1%"
    assert pct(5.8) == "5,8%"


def test_dates_and_durations() -> None:
    assert wd_dm(date(2026, 12, 22)) == "wt 22.12"
    assert wd_dm(date(2027, 3, 20)) == "sob 20.03"
    assert long_day(date(2026, 11, 4)) == "środa, 4 listopada"
    assert duration(18 * 60 + 35) == "18 h 35"
    assert duration(18 * 60) == "18 h"


def test_polish_plurals() -> None:
    assert [plural(n, "oferta", "oferty", "ofert") for n in (1, 3, 14, 22, 25)] == [
        "oferta",
        "oferty",
        "ofert",
        "oferty",
        "ofert",
    ]
