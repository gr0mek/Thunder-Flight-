"""Formatowanie liczb, dat i czasów po polsku – wspólne dla Telegrama i panelu."""

from __future__ import annotations

from datetime import date, datetime, time

NBSP = " "
MINUS = "−"

WEEKDAYS = ("pn", "wt", "śr", "czw", "pt", "sob", "nd")
WEEKDAYS_LONG = ("poniedziałek", "wtorek", "środa", "czwartek", "piątek", "sobota", "niedziela")
MONTHS_GEN = (
    "stycznia", "lutego", "marca", "kwietnia", "maja", "czerwca",
    "lipca", "sierpnia", "września", "października", "listopada", "grudnia",
)  # fmt: skip
MONTHS_NOM = (
    "styczeń", "luty", "marzec", "kwiecień", "maj", "czerwiec",
    "lipiec", "sierpień", "wrzesień", "październik", "listopad", "grudzień",
)  # fmt: skip


def group(n: int, sep: str = NBSP) -> str:
    """12345 → '12 345' (separator tysięcy: twarda spacja, żeby kwota się nie łamała)."""
    sign = MINUS if n < 0 else ""
    return sign + f"{abs(n):,}".replace(",", sep)


def zl(minor: int, sep: str = NBSP) -> str:
    """Kwota w groszach → '10 840 zł' (zaokrąglona do pełnych złotych)."""
    whole = (abs(minor) + 50) // 100
    return f"{group(-whole if minor < 0 else whole, sep)}{sep}zł"


def zl_signed(minor: int, sep: str = NBSP) -> str:
    """Różnica kwot ze znakiem: '+420 zł', '−120 zł'."""
    return ("+" if minor > 0 else "") + zl(minor, sep)


def decimal(x: float, digits: int = 1) -> str:
    """3.14 → '3,1'; bez końcowego ',0' gdy liczba jest całkowita."""
    s = f"{abs(x):.{digits}f}"
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return (MINUS if x < 0 and s != "0" else "") + s.replace(".", ",")


def pct(x: float, digits: int = 1, signed: bool = False) -> str:
    """Procent: '5,8%', ze znakiem '−3,1%' / '+2%'."""
    plus = "+" if signed and x > 0 else ""
    return f"{plus}{decimal(x, digits)}%"


def dm(d: date) -> str:
    """'22.12'"""
    return f"{d.day}.{d.month:02d}"


def wd_dm(d: date) -> str:
    """'wt 22.12'"""
    return f"{WEEKDAYS[d.weekday()]} {dm(d)}"


def long_day(d: date) -> str:
    """'środa, 4 listopada' – separator dnia w czacie."""
    return f"{WEEKDAYS_LONG[d.weekday()]}, {d.day} {MONTHS_GEN[d.month - 1]}"


def hm(t: time | datetime) -> str:
    """'07:30'"""
    return f"{t.hour:02d}:{t.minute:02d}"


def duration(minutes: int) -> str:
    """1115 → '18 h 35'; pełne godziny → '18 h'."""
    h, m = divmod(minutes, 60)
    return f"{h} h {m:02d}" if m else f"{h} h"


def hours(h: float) -> str:
    """37.9 → '37,9 h'"""
    return f"{decimal(h)} h"


def plural(n: int, one: str, few: str, many: str) -> str:
    """Polska odmiana: 1 oferta, 3 oferty, 14 ofert."""
    if n == 1:
        return one
    if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
        return few
    return many
