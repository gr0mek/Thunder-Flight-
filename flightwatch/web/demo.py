"""Dane przykładowe panelu – scenariusz z projektu UI (środa 4.11.2026, skan 07:30).

Panel czyta wyłącznie z tego modułu, dopóki nie powstanie `db/repo.py` (sesje 1–4).
Kwoty w złotych (całe), przeliczane na grosze przy wyświetlaniu.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Status = Literal["ok", "unknown", "estimated"]

THRESHOLD = 11_000
NEAR_LIMIT = 11_770  # próg + 7%
HOUR_VALUE = 30  # zł za godzinę podróży
TRANSFER = {"WAW": 200, "KRK": 600, "GDN": 600, "BER": 900}

HEADER_STATUS = "śr 4.11 · ostatni skan 07:30 · następny 19:30"
WATCH_TAG = "waw-dps-2026 · 2+1"


# ---------------------------------------------------------------------------
# Przegląd
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Decision:
    label: str
    best: int
    blocker: str
    best_qualifying: int
    median: int
    google: str
    deadline: str
    days_left: int


DECISION = Decision(
    label="BLISKO",
    best=11_180,
    blocker="Nie kwalifikuje się do KUP: warunki zmiany powrotu nieznane "
    "(brak reguły w fare_rules.yaml dla TK / EcoFly).",
    best_qualifying=11_420,
    median=12_050,
    google="niska",
    deadline="15.11",
    days_left=11,
)

BEST_DAILY = (
    12940, 12880, 12910, 12750, 12800, 12690, 12620, 12700, 12540, 12480, 12510, 12390, 12300,
    12350, 12210, 12120, 12180, 11990, 11920, 11870, 11760, 11640, 11590, 11420, 11180,
)  # fmt: skip
CHART_X_LABELS = ("11.10", "18.10", "25.10", "1.11", "4.11")

HEAT_DAYS = ("20.12", "21.12", "22.12", "23.12", "24.12", "25.12", "26.12", "27.12", "28.12", "29.12",
             "30.12", "31.12")  # fmt: skip
HEAT = {  # tys. zł, najniższa z wszystkich powrotów
    "WAW": (11.9, 11.18, 11.42, 12.1, 12.6, 12.4, 12.0, 12.3, 12.8, 13.1, 12.9, 12.5),
    "KRK": (12.3, 12.0, 11.82, 12.5, 13.0, 12.8, 12.3, 12.6, 13.2, 13.4, 13.1, 12.7),
    "GDN": (12.6, 12.4, 12.08, 12.8, 13.3, 13.0, 12.7, 12.9, 13.5, 13.7, 13.3, 13.0),
    "BER": (11.7, 11.51, 11.6, 11.9, 12.4, 12.2, 11.8, 12.0, 12.6, 12.9, 12.6, 12.3),
}
HEAT_K_EXTRA = {"WAW": 1.33, "KRK": 1.95, "GDN": 1.77, "BER": 1.99}  # dojazd + czas + kary, tys. zł


@dataclass(frozen=True)
class Budget:
    name: str
    used: int
    limit: int
    projection: int
    note: str


BUDGETS = (
    Budget("Ignav", 908, 8000, 6600, "kreska = prognoza na 30.11 (6 600) · alert przy 80%"),
    Budget("SerpApi", 9, 250, 60, "prognoza 60 · 1–2 zapytania dziennie"),
)

RECENT_RUNS = (
    ("4.11 07:30", "pełny · 192 zap. · 3 min 12 s", True),
    ("3.11 19:30", "potwierdzenie · top 20", True),
    ("3.11 10:14", "spadek ≥ 5% · live 1 oferta", True),
    ("3.11 07:30", "pełny · 4 błędy parsowania (2%)", False),
    ("2.11 19:30", "potwierdzenie · top 20", True),
)

HEALTH_CHIPS = ("heartbeat ✓", "bot online ✓", "NBP 4.11 ✓", "dysk 23%")


@dataclass(frozen=True)
class RankedOffer:
    id: str
    label: str
    origin: str
    airline: str
    via: str
    dates: str
    hours: float
    stops: int
    payable: int
    penalties: int
    penalties_why: str
    flex_short: str
    flex: str
    qualifies: bool
    age_min: int
    out: str
    back: str
    booking_url: str

    @property
    def transfer(self) -> int:
        return TRANSFER[self.origin]

    @property
    def time_cost(self) -> int:
        return round(self.hours * HOUR_VALUE)

    @property
    def k(self) -> int:
        return self.payable + self.transfer + self.time_cost + self.penalties


RANKING = (
    RankedOffer("qr", "Kompromis", "WAW", "Qatar", "DOH", "22.12 / 20.03", 37.9, 1, 11420, 0, "brak",
                "600 zł/os.", "Zmiana powrotu: 600 zł/os. + różnica taryfy (fare_rules: QR Economy Classic)",
                True, 14, "wt 22.12 Warszawa 15:55 → śr 23.12 Denpasar 09:30 · 18 h 35",
                "sob 20.03 Denpasar 19:50 → nd 21.03 Warszawa 09:15 · 19 h 25",
                "https://www.qatarairways.com/"),
    RankedOffer("ek", "Najszybsza", "BER", "Emirates", "DXB", "21.12 / 20.03", 36.5, 1, 11510, 0, "brak",
                "450 zł/os.", "Zmiana powrotu: 450 zł/os. (fare_rules: EK Economy Flex)",
                True, 14, "pn 21.12 Berlin 14:20 → wt 22.12 Denpasar 10:10 · 17 h 50",
                "sob 20.03 Denpasar 21:15 → nd 21.03 Berlin 08:55 · 18 h 40",
                "https://www.emirates.com/"),
    RankedOffer("qr2", "—", "GDN", "Qatar", "DOH", "22.12 / 15.03", 39, 1, 12080, 0, "brak",
                "600 zł/os.", "Zmiana powrotu: 600 zł/os. + różnica taryfy",
                True, 14, "wt 22.12 Gdańsk 13:40 → śr 23.12 Denpasar 09:30 · 19 h 50",
                "pn 15.03 Denpasar 19:50 → wt 16.03 Gdańsk 10:00 · 19 h 10",
                "https://www.qatarairways.com/"),
    RankedOffer("lh", "—", "KRK", "Lufthansa", "FRA, SIN", "22.12 / 20.03", 45, 2, 11820, 600,
                "2 dodatkowe przesiadki", "700 zł/os.", "Zmiana powrotu: 700 zł/os. (fare_rules: LH Economy Classic)",
                True, 14, "wt 22.12 Kraków 06:10 → śr 23.12 Denpasar 11:20 · 23 h 10",
                "sob 20.03 Denpasar 17:30 → nd 21.03 Kraków 08:20 · 21 h 50",
                "https://www.lufthansa.com/"),
    RankedOffer("tk", "Najtańsza", "WAW", "Turkish", "IST, SIN", "21.12 / 25.03", 47.5, 2, 11180, 2000,
                "przesiadki, noc, brak elastyczności", "nieznane",
                "Warunki zmiany nieznane – brak reguły TK EcoFly w fare_rules.yaml (kara 1 000 zł)",
                False, 14, "pn 21.12 Warszawa 19:05 → wt 22.12 Denpasar 18:45 · 23 h 40",
                "czw 25.03 Denpasar 08:10 → pt 26.03 Warszawa 07:00 · 23 h 50",
                "https://www.turkishairlines.com/"),
)  # fmt: skip


# ---------------------------------------------------------------------------
# Oferty
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OfferRow:
    origin: str
    airline: str
    via: str
    dates: str
    hours: float
    stops: int
    payable: int
    flex: str
    status: Status
    age: str

    @property
    def penalties(self) -> int:
        return (600 if self.stops > 1 else 0) + (1000 if self.status == "unknown" else 0)

    @property
    def k(self) -> int:
        return self.payable + TRANSFER[self.origin] + round(self.hours * HOUR_VALUE) + self.penalties

    @property
    def per_adult(self) -> int:
        # SZACUNEK z projektu: udział dorosłego w cenie grupy 2+1; docelowo per_adult_pln_minor z oferty
        return round(self.payable * 0.367 / 10) * 10


OFFERS = (
    OfferRow("WAW", "Turkish", "IST, SIN", "21.12 / 25.03", 47.5, 2, 11180, "nieznane", "unknown", "14 min"),
    OfferRow("WAW", "Qatar", "DOH", "22.12 / 20.03", 37.9, 1, 11420, "600 zł/os.", "ok", "14 min"),
    OfferRow("BER", "Emirates", "DXB", "21.12 / 20.03", 36.5, 1, 11510, "450 zł/os.", "ok", "14 min"),
    OfferRow("BER", "Qatar", "DOH", "22.12 / 20.03", 38.2, 1, 11600, "600 zł/os.", "ok", "3 h"),
    OfferRow("KRK", "Lufthansa", "FRA, SIN", "22.12 / 20.03", 45, 2, 11820, "700 zł/os.", "ok", "14 min"),
    OfferRow("WAW", "Emirates", "DXB", "20.12 / 15.03", 37.1, 1, 11900, "450 zł/os.", "ok", "3 h"),
    OfferRow("KRK", "Turkish", "IST", "22.12 / 25.03", 40.2, 1, 12000, "nieznane", "unknown", "14 min"),
    OfferRow("GDN", "Qatar", "DOH", "22.12 / 15.03", 39, 1, 12080, "600 zł/os.", "ok", "14 min"),
    OfferRow("BER", "Singapore", "SIN", "23.12 / 20.03", 41.5, 1, 12140, "bezpłatna", "ok", "12 h"),
    OfferRow("WAW", "KLM", "AMS, SIN", "21.12 / 31.03", 44.8, 2, 12230, "—", "estimated", "12 h"),
    OfferRow("GDN", "Lufthansa", "FRA, SIN", "21.12 / 20.03", 46.3, 2, 12390, "700 zł/os.", "ok", "14 min"),
    OfferRow("KRK", "Qatar", "DOH", "27.12 / 25.03", 38.6, 1, 12950, "600 zł/os.", "ok", "3 h"),
)
ORIGINS = ("WAW", "KRK", "GDN", "BER")


# ---------------------------------------------------------------------------
# Skany
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Scan:
    id: str
    when: str
    mode: str
    queries: str
    cache: str
    errors: str
    duration: str
    providers: str
    ok: bool


SCAN_STATS = (("Skany od 11.10", "50 / 50"), ("Trafienia cache", "18%"), ("Błędy parsowania", "0,6%"),
              ("Awaryjnie fast-flights", "3 razy"))  # fmt: skip

SCANS = (
    Scan("s1", "4.11 07:30", "Pełny", "192", "0", "0", "3:12", "Ignav", True),
    Scan("s2", "3.11 19:30", "Potwierdzenie", "20", "0", "0", "0:24", "Ignav", True),
    Scan("s3", "3.11 10:14", "Spadek ≥ 5%", "1", "—", "0", "0:03", "Ignav", True),
    Scan("s4", "3.11 07:30", "Pełny", "192", "12", "4", "3:40", "Ignav", True),
    Scan("s5", "2.11 19:30", "Potwierdzenie", "20", "0", "0", "0:22", "Ignav", True),
    Scan("s6", "2.11 07:30", "Pełny", "192", "0", "31", "5:58", "Ignav → fast-flights (30)", False),
    Scan("s7", "1.11 19:30", "Potwierdzenie", "20", "0", "0", "0:25", "Ignav", True),
    Scan("s8", "1.11 07:30", "Pełny", "192", "0", "0", "3:08", "Ignav", True),
)


# ---------------------------------------------------------------------------
# Reguły taryf – brakujące (wyliczane docelowo z ofert bez reguły)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MissingRule:
    code: str
    airline: str
    brand: str
    offers_24h: int
    best: int


MISSING_RULES = (
    MissingRule("TK", "Turkish Airlines", "EcoFly", 14, 11_180),
    MissingRule("KL", "KLM", "Economy Light", 3, 12_230),
)


# ---------------------------------------------------------------------------
# Konfiguracja (podgląd config.yaml)
# ---------------------------------------------------------------------------

CONFIG_HASH = "config_hash 3f9a1c · 3.10 22:41"

CONFIG_GROUPS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    ("Podróż", (("Pasażerowie", "2 dorosłych + dziecko (4)"), ("Wylot z", "WAW, KRK, GDN, BER"),
                ("Dolot (sesja 6)", "WMI, VIE, PRG, BUD"), ("Wylot", "20–31.12.2026"),
                ("Przylot DPS", "05:00–12:59"), ("Powrót", "15, 20, 25, 31.03.2027"),
                ("Bez przylotu", "00:00–05:59"))),
    ("Decyzja", (("Próg KUP", "11 000 zł"), ("BLISKO", "do +7% (11 770 zł)"), ("Termin", "15.11 · ostrzeżenie 8.11"),
                 ("Wiek ceny live", "≤ 60 min"), ("Ponowny KUP", "po spadku ≥ 3%"),
                 ("Mistake fare", "< 50% mediany, ≥ 7 dni"))),
    ("Koszt K", (("Godzina podróży", "30 zł"), ("Dodatkowa przesiadka", "300 zł"), ("Ponad 30 h", "100 zł/h"),
                 ("Nocna przesiadka", "400 zł (01–05)"), ("Brak elastyczności", "1 000 zł"),
                 ("Nieznane warunki", "jak brak elastyczności"))),
    ("Filtry", (("Maks. czas", "24 h (do 30 h z karą)"), ("Przesiadki", "maks. 2, preferowana 1"),
                ("Min. przesiadka", "120 min"), ("Bagaż / os.", "1 rejestrowany + 1 podręczny"),
                ("Miejsca", "obok siebie"))),
    ("Harmonogram", (("Skan pełny", "07:30"), ("Potwierdzenie", "19:30 · top 20"), ("Google", "08:00"),
                     ("Raport dzienny", "20:30"), ("Raport tygodniowy", "niedziela 18:00"),
                     ("Spadek → live", "≥ 5%"))),
    ("Dostawcy", (("Ignav", "główny · 8 000/mies."), ("SerpApi", "ocena Google · 250/mies."),
                  ("fast-flights", "awaryjny · 30/przebieg"), ("Travelpayouts", "wyłączony"), ("Cache", "60 min"))),
)  # fmt: skip

IGNAV_PLAN_NOTE = "4 lotniska × 12 dat × 4 powroty = 192 rano + top 20 wieczorem"
IGNAV_PLAN_SEGMENTS = (  # (etykieta, zapytań, szerokość paska %, kolor)
    ("skany pełne", 5760, 72, "accent"),
    ("potwierdzenia", 600, 8, "accent-600"),
    ("rezerwa 15%", 1200, 15, "neutral-600"),
)
IGNAV_PLAN_SPARE = 440
IGNAV_PLAN_LIMIT = 8000
