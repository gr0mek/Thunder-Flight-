"""Scenariusz z projektu (ekrany 01–10) zbudowany z prawdziwych formaterów.

`python -m flightwatch.alerts.preview` wypisuje wszystkie wiadomości; panel pokazuje je
pod /telegram w ramkach telefonu.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time

from flightwatch.alerts import format as f

PAX = 3
THRESHOLD = 1_100_000
URL = "https://www.qatarairways.com/booking"


@dataclass(frozen=True)
class UserMsg:
    text: str


@dataclass(frozen=True)
class Day:
    day: date


@dataclass(frozen=True)
class Bot:
    message: f.Message
    at: str  # godzina pod dymkiem, np. "08:02" albo "24.11 07:41"
    stripe: str | None = None  # pasek z lewej w podglądzie: "accent" | "neutral"


Item = UserMsg | Day | Bot


@dataclass(frozen=True)
class Screen:
    number: str
    title: str
    clock: str  # pasek stanu telefonu
    status: str
    items: tuple[Item, ...]
    admin: bool = False


def _dt(y: int, mo: int, d: int, h: int, mi: int) -> datetime:
    return datetime(y, mo, d, h, mi)


QR_OUT = f.Leg(_dt(2026, 12, 22, 15, 55), "Warszawa", _dt(2026, 12, 23, 9, 30), "Denpasar", 18 * 60 + 35)
QR_RET = f.Leg(_dt(2027, 3, 20, 19, 50), "Denpasar", _dt(2027, 3, 21, 9, 15), "Warszawa", 19 * 60 + 25)
QR_TERMS = f.ChangeTerms(allowed=True, fee_per_person_minor=60_000, fare_difference=True)


def _qr(payable: int, per_adult: int) -> f.Offer:
    return f.Offer(
        origin="WAW", airline="Qatar Airways", airline_short="Qatar", via=("DOH",),
        out_date=date(2026, 12, 22), ret_date=date(2027, 3, 20),
        payable_minor=payable, per_adult_minor=per_adult, booking_url=URL, change=QR_TERMS,
        stops_text="1 przesiadka w Dosze", out_leg=QR_OUT, ret_leg=QR_RET, duration_min=QR_OUT.duration_min,
    )  # fmt: skip


TK = f.Offer(
    origin="WAW", airline="Turkish Airlines", airline_short="Turkish", via=("IST", "SIN"),
    out_date=date(2026, 12, 21), ret_date=date(2027, 3, 25),
    payable_minor=1_118_000, per_adult_minor=409_000, booking_url="https://www.turkishairlines.com/",
    change=f.ChangeTerms(allowed=None), stops_text="2 przesiadki", duration_min=23 * 60 + 40,
)  # fmt: skip
EK = f.Offer(
    origin="BER", airline="Emirates", airline_short="Emirates", via=("DXB",),
    out_date=date(2026, 12, 21), ret_date=date(2027, 3, 20),
    payable_minor=1_151_000, per_adult_minor=421_000, booking_url="https://www.emirates.com/",
    change=f.ChangeTerms(allowed=True, fee_per_person_minor=45_000), stops_text="1 przes. (DXB)",
    duration_min=17 * 60 + 50,
)  # fmt: skip
EY = f.Offer(
    origin="GDN", airline="Etihad", airline_short="Etihad", via=("AUH",),
    out_date=date(2026, 12, 27), ret_date=date(2027, 3, 20),
    payable_minor=552_000, per_adult_minor=202_000, booking_url="https://www.etihad.com/",
    change=f.ChangeTerms(allowed=True, fee_per_person_minor=50_000), stops_text="1 przes. w Abu Zabi",
)  # fmt: skip

BUDGETS = (f.BudgetLine("Ignav", 908, 8000, forecast=6600, reserve=1200), f.BudgetLine("SerpApi", 9, 250))

WATCH = f.WatchSummary(
    name="Bali – zima 2026/27",
    route="WAW · KRK · GDN · BER → Bali",
    passengers="2 dorosłych + dziecko (4)",
    out_window=(date(2026, 12, 20), date(2026, 12, 31)),
    ret_window=(date(2027, 3, 15), date(2027, 3, 31)),
    threshold_minor=THRESHOLD,
)


def screens() -> tuple[Screen, ...]:
    qr = _qr(1_084_000, 398_000)
    top3_lines = (
        f.RankedLine("Kompromis", "WAW", 1_084_000, 38, 1),
        f.RankedLine("Najszybsza", "BER", 1_151_000, 36.5, 1),
        f.RankedLine("Najtańsza", "WAW", 1_079_000, 47, 2, warning="warunki nieznane"),
    )
    return (
        Screen("01", "Alert KUP", "08:03", "5G · 82%", (
            Bot(f.buy_alert(
                qr, pax=PAX, threshold_minor=THRESHOLD, live_age_min=4,
                ancillaries="Bagaż 3×23 kg i podręczny w cenie · miejsca obok siebie +240 zł (wliczone)",
                top3=top3_lines,
            ), "08:02", "accent"),
        )),
        Screen("02", "BLISKO (raz dziennie) i TERMIN (8.11)", "20:41", "5G · 64%", (
            Day(date(2026, 11, 4)),
            Bot(f.near_alert(
                TK, pax=PAX, threshold_minor=THRESHOLD, median_minor=1_205_000, google="cena niska",
                blocker="Warunki zmiany powrotu nieznane – nie może dać KUP. Sprawdź taryfę na stronie.",
            ), "20:31"),
            Day(date(2026, 11, 8)),
            Bot(f.deadline_alert(
                days_left=7, deadline=date(2026, 11, 15), threshold_minor=THRESHOLD,
                options=(
                    ("Najtańsza", "WAW", date(2026, 12, 21), 1_124_000),
                    ("Kompromis", "WAW", date(2026, 12, 22), 1_146_000),
                    ("Najszybsza", "BER", date(2026, 12, 21), 1_153_000),
                ),
                trend_pct=-2.9, note="Kompromis jest 4,2% nad progiem i ma elastyczny powrót.",
            ), "18:00", "neutral"),
        )),
        Screen("03", "MISTAKE_FARE i /status", "11:20", "5G · 71%", (
            Bot(f.mistake_fare_alert(EY, pax=PAX, median_minor=1_205_000, live_age_min=2), "10:58", "accent"),
            UserMsg("/status"),
            Bot(f.status_reply(f.StatusView(
                watch_name=WATCH.name, last_scan="dziś 07:30 · pełny · 192 zap. ✓",
                best_today_minor=1_118_000, best_today_decision="BLISKO",
                median_minor=1_205_000, median_change_pct=-7.2,
                google="cena niska (typowo 11,8–14,2 tys.)", budgets=BUDGETS,
                next_run="19:30 potwierdzenie top 20",
            )), "11:19"),
        )),
        Screen("04", "/top3", "21:05", "Wi-Fi · 58%", (
            UserMsg("/top3"),
            Bot(f.top3_reply((
                f.Top3Entry("cheapest", TK, "2 przes. (IST, SIN) · nocna przesiadka", 20_000, 1_480_500),
                f.Top3Entry("fastest", EK, "1 przes. (DXB)", 90_000, 1_350_500),
                f.Top3Entry("compromise", _qr(1_142_000, 418_000), "1 przes. (DOH)", 20_000, 1_275_700,
                            lowest_k=True),
            ), scan_at=time(19, 30)), "21:05"),
        )),
        Screen("05", "/kupione (z potwierdzeniem) i /budzet", "08:21", "5G · 80%", (
            UserMsg("/budzet"),
            Bot(f.budget_reply(month="listopad", lines=BUDGETS, fallback_used=0, fallback_limit=30), "08:19"),
            UserMsg("/kupione"),
            Bot(f.purchase_confirm(WATCH.name), "08:20"),
            Bot(f.purchase_done(), "08:21"),
        )),
        Screen("06", "Raport dzienny (20:30) i tygodniowy (nd 18:00)", "18:02", "Wi-Fi · 77%", (
            Day(date(2026, 10, 31)),
            Bot(f.daily_report(
                day=date(2026, 10, 31), best_minor=1_164_000, best_prev_minor=1_176_000,
                threshold_minor=THRESHOLD, queries=212, errors=0,
            ), "20:30"),
            Day(date(2026, 11, 1)),
            Bot(f.weekly_report(f.WeeklyReport(
                start=date(2026, 10, 26), end=date(2026, 11, 1), best_minor=1_159_000, median_minor=1_212_000,
                trend_pct=-4.1, days_to_deadline=14,
                by_origin=(("WAW", 1_159_000), ("BER", 1_162_000), ("KRK", 1_198_000), ("GDN", 1_223_000)),
                cheapest_dates="21.12 i 22.12 · najdrożej 29–30.12",
                outlook="Przy obecnym trendzie próg 11 000 zł możliwy ok. 12.11. Google ocenia ceny jako niskie.",
                scans_ok=14, scans_total=14, ignav_month=908,
            )), "18:00"),
        )),
        Screen("07", "Alerty techniczne 🛠", "09:12", "5G · 90%", (
            Bot(f.admin_budget(provider="Ignav", used=6400, limit=8000, day=date(2026, 11, 24),
                               exhausted_on=date(2026, 11, 29), fallback="fast-flights"), "24.11 07:41"),
            Bot(f.admin_parse_errors(run="scan full 07:30", failed=44, total=192, provider="ignav",
                                     hint="nowe pole fare_brand?", raw_dir="data/raw/2026-11-25"), "25.11 07:36"),
            Bot(f.admin_fx_stale(currency="USD", rate="3,94", rate_date=date(2026, 11, 21), age_days=4),
                "25.11 07:30"),
            Bot(f.admin_provider_error(provider="SerpApi", status=401, effect="Ocena Google pominięta."),
                "26.11 08:00"),
            Bot(f.admin_scan_missing(hours_since=26, last_ok=_dt(2026, 11, 26, 7, 30), check="scan_full",
                                     unit="flightwatch-scan-full.timer"), "27.11 09:31", "accent"),
        ), admin=True),
        Screen("08", "/start, /help i stan przed pierwszym skanem", "21:14", "Wi-Fi · 66%", (
            UserMsg("/start"),
            Bot(f.start_reply(WATCH), "21:14"),
            Bot(f.help_reply(), "21:14"),
            UserMsg("/top3"),
            Bot(f.no_data_reply(_dt(2026, 10, 11, 7, 30)), "21:15"),
        )),
        Screen("09", "Cena wygasła i ponowny KUP (spadek ≥ 3%)", "07:44", "5G · 91%", (
            Day(date(2026, 11, 6)),
            Bot(f.price_expired(qr, alert_sent_at=time(8, 2), now_minor=1_126_000, previous_minor=1_084_000,
                                next_confirm=time(19, 30)), "19:34"),
            Day(date(2026, 11, 7)),
            Bot(f.rebuy_alert(_qr(1_050_000, 386_000), pax=PAX, previous_minor=1_084_000, live_age_min=3),
                "07:43", "accent"),
        )),
        Screen("10", "Po zakupie: zmiana daty powrotu", "18:06", "5G · 70%", (
            Day(date(2026, 11, 15)),
            Bot(f.post_purchase_weekly(
                week=46, airline="Qatar", current_return=QR_RET.dep_at, return_city="Denpasar", pax=PAX,
                options=(
                    f.PriceChange(date(2027, 3, 15), 180_000, 3),
                    f.PriceChange(date(2027, 3, 25), 216_000, 9),
                    f.PriceChange(date(2027, 3, 31), None),
                ),
                change_note="25.03: −360 zł vs zeszły tydzień.", manage_url=URL,
            ), "18:00"),
            Day(date(2026, 11, 17)),
            Bot(f.seats_back(when=date(2027, 3, 31), fee_total_minor=240_000, pax=PAX), "07:36", "accent"),
        )),
    )  # fmt: skip


def main() -> None:
    for s in screens():
        print(f"\n===== {s.number} · {s.title} =====")
        for it in s.items:
            if isinstance(it, Day):
                print(f"\n        — {f.day_separator(it.day)} —")
            elif isinstance(it, UserMsg):
                print(f"\n{'':>40}» {it.text}")
            else:
                print(f"\n{it.message.text}\n[{it.at}]")
                for row in it.message.keyboard:
                    print("  " + "  ".join(f"[ {b.text} ]" for b in row))


if __name__ == "__main__":
    main()
