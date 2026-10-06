"""Teksty wiadomości Telegrama (parse_mode=HTML) i ich przyciski.

Każda funkcja jest czysta: dostaje gotowe dane widoku, zwraca `Message`.
Odpowiada ekranom 01–10 z projektu `FlightWatch UI.dc.html`. Telegram nie ma kolorów,
więc tekst drugorzędny (szary w projekcie) idzie kursywą, a nagłówki pogrubione.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, time
from html import escape

from flightwatch.text import (
    dm,
    duration,
    group,
    hm,
    long_day,
    pct,
    plural,
    wd_dm,
    zl,
    zl_signed,
)

ADMIN_PREFIX = "🛠"  # config.yaml → alerts.admin_prefix


# ---------------------------------------------------------------------------
# Typy wyjściowe
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Button:
    """Przycisk inline: z linkiem (`url`) albo z akcją bota (`callback`)."""

    text: str
    url: str | None = None
    callback: str | None = None

    def __post_init__(self) -> None:
        if (self.url is None) == (self.callback is None):
            raise ValueError("Przycisk potrzebuje dokładnie jednego z: url, callback")

    def to_api(self) -> dict[str, str]:
        if self.url is not None:
            return {"text": self.text, "url": self.url}
        assert self.callback is not None
        return {"text": self.text, "callback_data": self.callback}


@dataclass(frozen=True)
class Message:
    text: str
    keyboard: tuple[tuple[Button, ...], ...] = ()

    def to_api(self) -> dict[str, object]:
        """Ciało wywołania sendMessage (bez chat_id)."""
        body: dict[str, object] = {
            "text": self.text,
            "parse_mode": "HTML",
            "link_preview_options": {"is_disabled": True},
        }
        if self.keyboard:
            body["reply_markup"] = {"inline_keyboard": [[b.to_api() for b in row] for row in self.keyboard]}
        return body


# ---------------------------------------------------------------------------
# Dane wejściowe (widoki przygotowane przez silnik / repozytorium)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Leg:
    """Jeden kierunek w czasie lokalnym lotnisk."""

    dep_at: datetime
    dep_city: str
    arr_at: datetime
    arr_city: str
    duration_min: int

    def line(self) -> str:
        return (
            f"{wd_dm(self.dep_at.date())} {escape(self.dep_city)} {hm(self.dep_at)} · "
            f"{wd_dm(self.arr_at.date())} {escape(self.arr_city)} {hm(self.arr_at)} "
            f"({duration(self.duration_min)})"
        )


@dataclass(frozen=True)
class ChangeTerms:
    """Warunki zmiany daty powrotu. `allowed=None` = nieznane (brak reguły taryfy)."""

    allowed: bool | None
    fee_per_person_minor: int = 0
    fare_difference: bool = False

    def text(self) -> str:
        if self.allowed is None:
            return "nieznane"
        if not self.allowed:
            return "niedozwolona"
        if self.fee_per_person_minor == 0:
            return "bezpłatna"
        s = f"{zl(self.fee_per_person_minor)}/os."
        return s + (" + różnica taryfy" if self.fare_difference else "")


@dataclass(frozen=True)
class Offer:
    origin: str  # IATA
    airline: str  # "Qatar Airways"
    airline_short: str  # "Qatar"
    via: tuple[str, ...]  # ("DOH",)
    out_date: date
    ret_date: date
    payable_minor: int  # kwota do zapłaty za całą grupę
    per_adult_minor: int
    booking_url: str
    change: ChangeTerms
    stops_text: str = ""  # "1 przesiadka w Dosze"
    out_leg: Leg | None = None
    ret_leg: Leg | None = None
    duration_min: int | None = None  # tam, gdy brak pełnych odcinków


@dataclass(frozen=True)
class RankedLine:
    """Wiersz „Top 3” pod alertem KUP."""

    label: str  # Kompromis / Najszybsza / Najtańsza
    origin: str
    payable_minor: int
    total_hours: float
    stops: int
    warning: str | None = None


@dataclass(frozen=True)
class Top3Entry:
    kind: str  # cheapest | fastest | compromise
    offer: Offer
    stops_detail: str  # "2 przes. (IST, SIN) · nocna przesiadka"
    transfer_minor: int  # dojazd na lotnisko
    effective_cost_minor: int  # K
    lowest_k: bool = False


TOP3_LABELS = {"cheapest": "💰 Najtańsza", "fastest": "⚡ Najszybsza", "compromise": "⚖️ Kompromis"}


@dataclass(frozen=True)
class BudgetLine:
    name: str
    used: int
    limit: int
    forecast: int | None = None
    reserve: int | None = None


@dataclass(frozen=True)
class WatchSummary:
    name: str  # "Bali – zima 2026/27"
    route: str  # "WAW · KRK · GDN · BER → Bali"
    passengers: str  # "2 dorosłych + dziecko (4)"
    out_window: tuple[date, date]
    ret_window: tuple[date, date]
    threshold_minor: int


@dataclass(frozen=True)
class StatusView:
    watch_name: str
    last_scan: str  # "dziś 07:30 · pełny · 192 zap. ✓"
    best_today_minor: int
    best_today_decision: str  # BLISKO
    median_minor: int
    median_change_pct: float
    google: str  # "cena niska (typowo 11,8–14,2 tys.)"
    budgets: Sequence[BudgetLine]
    next_run: str  # "19:30 potwierdzenie top 20"


@dataclass(frozen=True)
class PriceChange:
    when: date
    fee_total_minor: int | None  # None = brak miejsc w taryfie
    seats: int = 0


# ---------------------------------------------------------------------------
# Pomocnicze
# ---------------------------------------------------------------------------


def _b(s: str) -> str:
    return f"<b>{s}</b>"


def _i(s: str) -> str:
    return f"<i>{s}</i>"


def _pax(n: int) -> str:
    return f"za {n} os."


def _join(*blocks: str | None) -> str:
    return "\n\n".join(b for b in blocks if b)


def _lines(*lines: str | None) -> str:
    return "\n".join(line for line in lines if line)


def _url(url: str) -> str:
    if not url.startswith("https://"):
        raise ValueError("Link do rezerwacji musi być https://")
    return url


# ---------------------------------------------------------------------------
# 01 · KUP  /  09 · KUP ponownie, cena wygasła
# ---------------------------------------------------------------------------


def buy_alert(
    o: Offer,
    *,
    pax: int,
    threshold_minor: int,
    live_age_min: int,
    ancillaries: str,
    top3: Sequence[RankedLine] = (),
    sent_at: time | None = None,
) -> Message:
    """🟢 KUP – oferta kwalifikująca się, cena live ≤ 60 min, kwota ≤ progu."""
    assert o.out_leg and o.ret_leg, "KUP wymaga pełnych odcinków"
    head = _lines(
        _b(f"🟢 KUP · {o.origin} → DPS"),
        _b(zl(o.payable_minor)),
        _i(f"do zapłaty {_pax(pax)} · {zl(o.per_adult_minor)} za dorosłego · próg {zl(threshold_minor)}"),
    )
    flight = _lines(
        f"{escape(o.airline)} · {escape(o.stops_text)}",
        f"→ {o.out_leg.line()}",
        f"← {o.ret_leg.line()}",
    )
    terms = _lines(
        f"Zmiana powrotu: {o.change.text()}",
        _i(escape(ancillaries)),
        _i(f"Cena live sprzed {live_age_min} min · potwierdzona"),
    )
    top = None
    if top3:
        rows = []
        for n, r in enumerate(top3, 1):
            row = f"{n}. {r.label} · {r.origin} · {zl(r.payable_minor)} · {_h(r.total_hours)} h · {r.stops} przes."
            if r.warning:
                row += f" ⚠ {escape(r.warning)}"
            rows.append(row)
        top = _lines(_b("TOP 3"), *rows)
    return Message(
        _join(head, flight, terms, top),
        (
            (Button(f"Rezerwuj w {o.airline_short} ↗", url=_url(o.booking_url)),),
            (Button("Pełne top 3", callback="top3"), Button("Kupione ✓", callback="bought")),
        ),
    )


def _h(h: float) -> str:
    return f"{h:.1f}".rstrip("0").rstrip(".").replace(".", ",")


def rebuy_alert(
    o: Offer,
    *,
    pax: int,
    previous_minor: int,
    live_age_min: int,
    ancillaries: str = "bagaż i miejsca wliczone",
) -> Message:
    """🟢 KUP ponownie – ta sama oferta spadła o ≥ rebuy_alert_drop_pct od ostatniego KUP."""
    assert o.out_leg and o.ret_leg
    drop = (o.payable_minor - previous_minor) / previous_minor * 100
    head = _lines(
        _b(f"🟢 KUP ponownie · {pct(drop, signed=True)}"),
        _b(zl(o.payable_minor)),
        _i(f"{_pax(pax)} · {zl(o.per_adult_minor)} za dorosłego · poprzedni KUP {zl(previous_minor)}"),
    )
    body = _lines(
        f"Ta sama oferta: {escape(o.airline_short)} · {o.origin} {dm(o.out_date)} / {dm(o.ret_date)}",
        f"{escape(o.stops_text)} · {duration(o.out_leg.duration_min)} / {duration(o.ret_leg.duration_min)}",
        f"Zmiana powrotu: {o.change.text()}",
        _i(f"Cena live sprzed {live_age_min} min · {escape(ancillaries)}"),
    )
    return Message(
        _join(head, body),
        (
            (Button(f"Rezerwuj w {o.airline_short} ↗", url=_url(o.booking_url)),),
            (Button("Pełne top 3", callback="top3"), Button("Kupione ✓", callback="bought")),
        ),
    )


def price_expired(o: Offer, *, alert_sent_at: time, now_minor: int, previous_minor: int, next_confirm: time) -> Message:
    """ℹ️ Cena z alertu KUP wygasła (potwierdzenie live pokazało wyższą kwotę)."""
    return Message(
        _lines(
            _b(f"ℹ️ Cena z alertu {hm(alert_sent_at)} wygasła"),
            f"{escape(o.airline_short)} · {o.origin} {dm(o.out_date)} – teraz {zl(now_minor)} "
            f"({zl_signed(now_minor - previous_minor)}). Nie jest już KUP.",
            _i(f"Następne potwierdzenie: {hm(next_confirm)}."),
        )
    )


# ---------------------------------------------------------------------------
# 02 · BLISKO i TERMIN  /  03 · MISTAKE_FARE
# ---------------------------------------------------------------------------


def near_alert(
    o: Offer,
    *,
    pax: int,
    threshold_minor: int,
    median_minor: int,
    google: str | None,
    blocker: str | None = None,
) -> Message:
    """🟡 BLISKO – najlepsza kwota w paśmie near_band_pct nad progiem (raz dziennie)."""
    over = o.payable_minor - threshold_minor
    route = f"{escape(o.airline_short)} · {o.origin} {dm(o.out_date)} → DPS · {escape(o.stops_text)}"
    if o.duration_min:
        route += f" · {duration(o.duration_min)}"
    ctx = f"Mediana 14 dni: {zl(median_minor)}" + (f" · Google: {escape(google)}" if google else "")
    return Message(
        _lines(
            _b(f"🟡 BLISKO · {zl(over)} nad progiem"),
            f"{_b(zl(o.payable_minor))} {_i(f'{_pax(pax)} · {zl(o.per_adult_minor)} za dorosłego')}",
            route,
            _i(f"⚠ {escape(blocker)}") if blocker else None,
            _i(ctx),
        ),
        ((Button("Otwórz ofertę ↗", url=_url(o.booking_url)), Button("Top 3", callback="top3")),),
    )


def deadline_alert(
    *,
    days_left: int,
    deadline: date,
    threshold_minor: int,
    options: Sequence[tuple[str, str, date, int]],
    trend_pct: float,
    note: str | None = None,
) -> Message:
    """⏳ TERMIN – ostrzeżenie przed terminem decyzji; opcje: (etykieta, lotnisko, data, kwota)."""
    rows = [f"{label} · {origin} {dm(d)} — {_b(zl(minor))}" for label, origin, d, minor in options]
    tail = f"Trend 7 dni: {pct(trend_pct)}." + (f" {escape(note)}" if note else "")
    return Message(
        _join(
            _lines(
                _b(f"⏳ TERMIN · {days_left} {plural(days_left, 'dzień', 'dni', 'dni')} do {dm(deadline)}"),
                f"Nie było oferty ≤ {zl(threshold_minor)}. Najlepsze opcje dziś:",
            ),
            _lines(*rows),
            _i(tail),
        )
    )


def mistake_fare_alert(o: Offer, *, pax: int, median_minor: int, live_age_min: int) -> Message:
    """⚡ MISTAKE FARE – kwota < 50% mediany (przy ≥ 7 dniach danych)."""
    drop = (o.payable_minor - median_minor) / median_minor * 100
    return Message(
        _lines(
            _b(f"⚡ MISTAKE FARE · {pct(drop, digits=0)} od mediany"),
            f"{_b(zl(o.payable_minor))} {_i(f'{_pax(pax)} · mediana {zl(median_minor)}')}",
            f"{escape(o.airline_short)} · {o.origin} {dm(o.out_date)} → DPS · {escape(o.stops_text)}",
            _i(
                f"Potwierdzona live {live_age_min} min temu. "
                "Takie ceny znikają w godzinach – linia może anulować bilet."
            ),
        ),
        ((Button(f"Rezerwuj w {o.airline_short} ↗", url=_url(o.booking_url)),),),
    )


# ---------------------------------------------------------------------------
# 03 /status · 04 /top3 · 05 /budzet i /kupione · 08 /start, /help
# ---------------------------------------------------------------------------


def _budget_short(b: BudgetLine) -> str:
    return f"{b.name} {b.used}/{b.limit}"


def status_reply(s: StatusView) -> Message:
    rows = [
        ("Ostatni skan", escape(s.last_scan)),
        ("Najlepsza dziś", f"{zl(s.best_today_minor)} ({s.best_today_decision})"),
        ("Mediana 14 d", f"{zl(s.median_minor)} · {pct(s.median_change_pct, signed=True)}"),
        ("Google", escape(s.google)),
        ("Budżet API", " · ".join(_budget_short(b) for b in s.budgets)),
        ("Następny", escape(s.next_run)),
    ]
    return Message(_lines(_b(f"Status · {escape(s.watch_name)}"), *(f"{_i(k)}: {v}" for k, v in rows)))


def top3_reply(entries: Sequence[Top3Entry], *, scan_at: time) -> Message:
    blocks = []
    for e in entries:
        o = e.offer
        unknown = o.change.allowed is None
        change = "⚠ warunki zmiany nieznane" if unknown else f"zmiana powrotu {o.change.text()}"
        k = f"K {group(round(e.effective_cost_minor / 100))}" + (" (najniższy)" if e.lowest_k else "")
        dur = duration(o.duration_min) if o.duration_min else ""
        transfer = f" · dojazd {zl(e.transfer_minor)}" if e.kind != "cheapest" else ""
        blocks.append(
            _lines(
                f"{_b(TOP3_LABELS[e.kind])} — {_b(zl(o.payable_minor))}",
                f"{escape(o.airline_short)} · {o.origin} {dm(o.out_date)} / {dm(o.ret_date)}",
                _i(f"{dur} · {escape(e.stops_detail)}{transfer}"),
                _i(f"{change} · {k}"),
            )
        )
    foot = _i("Kwoty za 3 os. z bagażem i miejscami. K = kwota + dojazd + czas + kary.")
    return Message(
        _join(_b(f"Top 3 · skan {hm(scan_at)}"), *blocks, foot),
        (tuple(Button(f"{e.offer.airline_short} ↗", url=_url(e.offer.booking_url)) for e in entries),),
    )


def _bar(pct_used: float, width: int = 10) -> str:
    filled = max(1 if pct_used > 0 else 0, min(width, round(pct_used / 100 * width)))
    return "▰" * filled + "▱" * (width - filled)


def budget_reply(*, month: str, lines: Sequence[BudgetLine], fallback_used: int, fallback_limit: int) -> Message:
    blocks = []
    for b in lines:
        p = b.used / b.limit * 100
        extra = None
        if b.forecast is not None:
            extra = f"Prognoza na koniec miesiąca: {group(b.forecast)}"
            if b.reserve is not None:
                extra += f" · rezerwa {group(b.reserve)}"
        blocks.append(
            _lines(
                f"{b.name}: {group(b.used)} / {group(b.limit)} · {round(p)}%",
                f"<code>{_bar(p)}</code>",
                _i(extra) if extra else None,
            )
        )
    tail = _i(f"fast-flights: {fallback_used} / {fallback_limit} dziś (zapas)")
    return Message(_join(_b(f"Budżet API · {month}"), *blocks, tail))


def purchase_confirm(watch_name: str, *, valid_min: int = 10) -> Message:
    """/kupione – wymaga potwierdzenia przyciskiem (ADR-005)."""
    return Message(
        _lines(
            _b(f"Zakończyć obserwację „{escape(watch_name)}”?"),
            "Przestanę wysyłać alerty zakupu. Włączę śledzenie zmiany daty powrotu.",
            _i(f"Potwierdzenie ważne {valid_min} min."),
        ),
        ((Button("Tak, kupione", callback="bought:yes"), Button("Anuluj", callback="bought:no")),),
    )


def purchase_done() -> Message:
    return Message(
        _lines(
            _b("✅ Zapisane. Udanej podróży!"),
            _i("Alerty zakupu wyłączone. Dam znać, gdy dopłata za zmianę powrotu się zmieni."),
        )
    )


def purchase_cancelled() -> Message:
    return Message("Anulowane – obserwacja trwa dalej.")


def start_reply(w: WatchSummary) -> Message:
    (o1, o2), (r1, r2) = w.out_window, w.ret_window
    rows = [
        ("Trasa", escape(w.route)),
        ("Pasażerowie", escape(w.passengers)),
        ("Daty", f"wylot {o1.day}–{dm(o2)} · powrót {r1.day}–{dm(r2)}"),
        ("Próg KUP", f"{zl(w.threshold_minor)} z bagażem i miejscami"),
    ]
    return Message(_lines(_b("Cześć! Obserwuję jedną podróż:"), *(f"{_i(k)}: {v}" for k, v in rows)))


COMMANDS = (
    ("status", "ostatni skan, najlepsza kwota, budżet"),
    ("top3", "najtańsza, najszybsza, kompromis"),
    ("budzet", "zużycie API"),
    ("kupione", "kończy alerty zakupu"),
)


def help_reply() -> Message:
    return Message(_lines(_b("Komendy"), *(f"/{c} – {d}" for c, d in COMMANDS)))


def no_data_reply(first_scan_at: datetime) -> Message:
    return Message(f"Jeszcze brak danych. Pierwszy skan: {wd_dm(first_scan_at.date())}, {hm(first_scan_at)}.")


# ---------------------------------------------------------------------------
# 06 · Raporty
# ---------------------------------------------------------------------------


def daily_report(
    *,
    day: date,
    best_minor: int,
    best_prev_minor: int,
    threshold_minor: int,
    queries: int,
    errors: int,
) -> Message:
    gap = best_minor - threshold_minor
    gap_text = f"Do progu brakuje {zl(gap)} ({pct(gap / threshold_minor * 100)})" if gap > 0 else "Poniżej progu"
    err = "bez błędów" if errors == 0 else f"{errors} {plural(errors, 'błąd', 'błędy', 'błędów')}"
    return Message(
        _lines(
            _b(f"Dzień · {dm(day)}"),
            f"Najlepsza: {_b(zl(best_minor))} ({zl_signed(best_minor - best_prev_minor)} vs wczoraj)",
            _i(f"{gap_text} · {queries} zapytań · {err}"),
        )
    )


@dataclass(frozen=True)
class WeeklyReport:
    start: date
    end: date
    best_minor: int
    median_minor: int
    trend_pct: float
    days_to_deadline: int
    by_origin: Sequence[tuple[str, int]]  # (IATA, kwota)
    cheapest_dates: str  # "21.12 i 22.12 · najdrożej 29–30.12"
    outlook: str
    scans_ok: int
    scans_total: int
    ignav_month: int


def weekly_report(r: WeeklyReport) -> Message:
    origins = " · ".join(f"{code} {group(round(m / 100))}" for code, m in r.by_origin)
    return Message(
        _join(
            _b(f"📊 Tydzień {dm(r.start)} – {dm(r.end)}"),
            _lines(
                f"{_i('Najlepsza')}: {_b(zl(r.best_minor))}",
                f"{_i('Mediana')}: {_b(zl(r.median_minor))}",
                f"{_i('Trend')}: {_b(pct(r.trend_pct) + ' / tydz.')}",
                f"{_i('Do terminu')}: {_b(f'{r.days_to_deadline} dni')}",
            ),
            _lines(_b("Najtańsze lotnisko"), origins),
            _lines(_b("Najtańsze daty wylotu"), escape(r.cheapest_dates)),
            escape(r.outlook),
            _i(f"Skany {r.scans_ok}/{r.scans_total} ✓ · Ignav w tym mies. {group(r.ignav_month)}"),
        )
    )


# ---------------------------------------------------------------------------
# 07 · Alerty techniczne 🛠
# ---------------------------------------------------------------------------


def _admin(title: str, body: str) -> Message:
    return Message(f"{ADMIN_PREFIX} {_b(escape(title))}\n<code>{escape(body)}</code>")


def admin_budget(*, provider: str, used: int, limit: int, day: date, exhausted_on: date, fallback: str) -> Message:
    p = round(used / limit * 100)
    return _admin(
        f"Budżet {provider} {p}%",
        f"{group(used, ' ')} / {group(limit, ' ')} · {dm(day)}. "
        f"Przy obecnym tempie 100% ok. {dm(exhausted_on)} → dalej {fallback}.",
    )


def admin_parse_errors(*, run: str, failed: int, total: int, provider: str, hint: str, raw_dir: str) -> Message:
    p = round(failed / total * 100)
    return _admin(
        f"Błędy parsowania {p}%",
        f"{run} · {failed}/{total} · {provider}: {hint} Surowe odpowiedzi w {raw_dir}.",
    )


def admin_fx_stale(*, currency: str, rate: str, rate_date: date, age_days: int) -> Message:
    return _admin(
        f"Kurs NBP sprzed {age_days} dni",
        f"{currency} {rate} z {dm(rate_date)}. Bez decyzji KUP do nowego kursu.",
    )


def admin_provider_error(*, provider: str, status: int, effect: str, remind_h: int = 24) -> Message:
    return _admin(
        f"{provider} {status}",
        f"Klucz odrzucony. {effect} Następne przypomnienie za {remind_h} h.",
    )


def admin_scan_missing(*, hours_since: int, last_ok: datetime, check: str, unit: str) -> Message:
    return _admin(
        f"Brak skanu od {hours_since} h",
        f"Ostatni udany: {dm(last_ok.date())} {hm(last_ok)}. healthchecks: {check} DOWN. "
        f"Sprawdź: systemctl status {unit}",
    )


# ---------------------------------------------------------------------------
# 10 · Po zakupie
# ---------------------------------------------------------------------------


def post_purchase_weekly(
    *,
    week: int,
    airline: str,
    current_return: datetime,
    return_city: str,
    pax: int,
    options: Sequence[PriceChange],
    change_note: str | None,
    manage_url: str,
) -> Message:
    rows = []
    for c in options:
        if c.fee_total_minor is None:
            rows.append(_i(f"{wd_dm(c.when)} — brak miejsc w taryfie"))
        else:
            seats = f"{c.seats} {plural(c.seats, 'miejsce', 'miejsca', 'miejsc')}"
            rows.append(f"{wd_dm(c.when)} — {zl(c.fee_total_minor)} · {seats}")
    return Message(
        _join(
            _lines(
                _b(f"✈️ Twój powrót · tydzień {week}"),
                f"Kupione: {escape(airline)}, powrót {wd_dm(current_return.date())} "
                f"z {escape(return_city)} {hm(current_return)}.",
            ),
            _lines(_b(f"Dopłata za zmianę, {pax} os."), *rows),
            _i(f"{escape(change_note)} Sprawdzam raz w tygodniu." if change_note else "Sprawdzam raz w tygodniu."),
        ),
        ((Button("Zarządzaj ↗", url=_url(manage_url)), Button("Wycisz", callback="mute:post_purchase")),),
    )


def seats_back(*, when: date, fee_total_minor: int, pax: int) -> Message:
    return Message(
        _lines(_b(f"✈️ Miejsca na {dm(when)} wróciły"), f"Dopłata za zmianę: {zl(fee_total_minor)} {_pax(pax)}")
    )


def day_separator(d: date) -> str:
    """Etykieta dnia jak w czacie – używana w podglądzie, nie wysyłana."""
    return long_day(d)


__all__ = [
    "ADMIN_PREFIX",
    "COMMANDS",
    "BudgetLine",
    "Button",
    "ChangeTerms",
    "Leg",
    "Message",
    "Offer",
    "PriceChange",
    "RankedLine",
    "StatusView",
    "Top3Entry",
    "WatchSummary",
    "WeeklyReport",
]
