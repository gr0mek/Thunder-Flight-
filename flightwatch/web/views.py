"""Widoki panelu: dane → słowniki gotowe do szablonów (czyste funkcje, bez I/O)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlencode

from flightwatch.fare_rules import FareRule, rule_id
from flightwatch.text import decimal, group, plural, zl
from flightwatch.web import demo

View = dict[str, Any]


def pln(v: int) -> str:
    """Złote (całe) → '11 420 zł'."""
    return zl(v * 100)


def href(path: str, params: Mapping[str, str | None], **change: str | None) -> str:
    """Link z zachowaniem bieżących parametrów (np. zaznaczenie wiersza + filtr)."""
    merged = {**params, **change}
    q = {k: v for k, v in merged.items() if v}
    return path + ("?" + urlencode(q) if q else "")


# ---------------------------------------------------------------------------
# 11 · Przegląd
# ---------------------------------------------------------------------------

CHART_W, CHART_H = 800, 230
CHART_LO, CHART_HI = 10_600, 13_200


def rolling_median(values: Sequence[int], window: int = 14) -> list[int]:
    out = []
    for i in range(len(values)):
        w = sorted(values[max(0, i - window + 1) : i + 1])
        out.append(w[len(w) // 2])
    return out


def _y(v: float) -> float:
    return CHART_H - (v - CHART_LO) / (CHART_HI - CHART_LO) * CHART_H


def _x(i: int, n: int) -> float:
    return i / (n - 1) * (CHART_W - 8) + 4


def chart_view(best: Sequence[int], show_band: bool) -> View:
    n = len(best)

    def pts(a: Sequence[int]) -> str:
        return " ".join(f"{_x(i, n):.1f},{_y(v):.1f}" for i, v in enumerate(a))

    return {
        "w": CHART_W,
        "h": CHART_H,
        "best_pts": pts(best),
        "median_pts": pts(rolling_median(best)),
        "thr_y": f"{_y(demo.THRESHOLD):.1f}",
        "band_y": f"{_y(demo.NEAR_LIMIT):.1f}",
        "band_h": f"{_y(demo.THRESHOLD) - _y(demo.NEAR_LIMIT):.1f}",
        "show_band": show_band,
        "last_x": f"{_x(n - 1, n):.1f}",
        "last_y": f"{_y(best[-1]):.1f}",
        "y_ticks": [
            {"label": f"{v // 1000} tys.", "top": f"{_y(v) / CHART_H * 100:.2f}%"} for v in (13000, 12000, 11000)
        ],
        "x_labels": demo.CHART_X_LABELS,
        "threshold": pln(demo.THRESHOLD).replace(" zł", ""),
        "near": pln(demo.NEAR_LIMIT).replace(" zł", ""),
    }


def heatmap_view(metric: str) -> View:
    rows = [
        (code, [v + demo.HEAT_K_EXTRA[code] if metric == "K" else v for v in arr]) for code, arr in demo.HEAT.items()
    ]
    all_v = [v for _, arr in rows for v in arr]
    lo, hi = min(all_v), max(all_v)
    ring_at = lo + 0.6 if metric == "K" else demo.NEAR_LIMIT / 1000
    out_rows = []
    for code, arr in rows:
        cells = []
        for i, v in enumerate(arr):
            t = (v - lo) / (hi - lo)
            p = round((1 - t) * 78 + 4)
            cells.append(
                {
                    "label": f"{v:.1f}".replace(".", ","),
                    "title": f"{code} {demo.HEAT_DAYS[i]}: {pln(round(v * 1000))}",
                    "pct": p,
                    "light": p > 55,
                    "ring": v <= ring_at + 1e-9,
                }
            )
        out_rows.append({"code": code, "cells": cells})
    return {
        "metric": metric,
        "days": demo.HEAT_DAYS,
        "rows": out_rows,
        "ring_legend": "w granicach 600 zł od najniższego K" if metric == "K" else "w paśmie BLISKO (≤ 11 770 zł)",
    }


def ranking_view(sel_id: str | None, params: Mapping[str, str | None]) -> View:
    offers = sorted(demo.RANKING, key=lambda o: o.k)
    sel = next((o for o in offers if o.id == sel_id), None) or next(o for o in offers if o.id == "qr")
    rows = [
        {
            "rank": i,
            "o": o,
            "hours": f"{decimal(o.hours)} h",
            "payable": pln(o.payable),
            "k": pln(o.k),
            "selected": o.id == sel.id,
            "href": href("/", params, sel=o.id) + "#ranking",
        }
        for i, o in enumerate(offers, 1)
    ]

    def share(v: int) -> str:
        return f"{v / sel.k * 100:.1f}%"

    if not sel.qualifies:
        qual = "Nie może wywołać KUP: nieznane warunki taryfy."
    elif sel.payable <= demo.THRESHOLD:
        qual = "Kwalifikuje się do KUP."
    else:
        qual = f"Kwalifikuje się do KUP, ale {pln(sel.payable - demo.THRESHOLD)} nad progiem."
    detail = {
        "o": sel,
        "stops": f"{sel.stops} {'przesiadka' if sel.stops == 1 else 'przesiadki'} ({sel.via})",
        "k": pln(sel.k),
        "hours": f"{decimal(sel.hours)} h",
        "parts": [
            {
                "name": "Kwota do zapłaty",
                "value": pln(sel.payable),
                "share": share(sel.payable),
                "color": "accent",
            },
            {
                "name": "Dojazd",
                "value": pln(sel.transfer),
                "share": share(sel.transfer),
                "color": "accent-600",
            },
            {
                "name": f"Czas ({decimal(sel.hours)} h × {demo.HOUR_VALUE} zł)",
                "value": pln(sel.time_cost),
                "share": share(sel.time_cost),
                "color": "neutral-500",
            },
            {
                "name": f"Kary · {sel.penalties_why}",
                "value": pln(sel.penalties),
                "share": share(sel.penalties),
                "color": "neutral-700",
            },
        ],
        "qualifies": qual,
    }
    return {"rows": rows, "sel": detail}


def overview_view(params: Mapping[str, str | None]) -> View:
    metric = "K" if params.get("metric") == "K" else "kwota"
    show_band = params.get("band") != "0"
    d = demo.DECISION
    over = d.best - demo.THRESHOLD
    budgets = [
        {
            "b": b,
            "used": group(b.used),
            "limit": group(b.limit),
            "pct": f"{b.used / b.limit * 100:.1f}%",
            "proj": f"{b.projection / b.limit * 100:.1f}%",
        }
        for b in demo.BUDGETS
    ]
    return {
        "decision": {
            "label": d.label,
            "blocker": d.blocker,
            "google": d.google,
            "deadline": d.deadline,
            "days_left": d.days_left,
            "best": pln(d.best),
            "over": f"{pln(over)} ({decimal(over / demo.THRESHOLD * 100)}%) nad progiem {pln(demo.THRESHOLD)}",
            "best_qualifying": pln(d.best_qualifying),
            "median": pln(d.median),
        },
        "chart": chart_view(demo.BEST_DAILY, show_band),
        "heat": heatmap_view(metric),
        "heat_href": {m: href("/", params, metric=m if m == "K" else None) + "#heatmap" for m in ("kwota", "K")},
        "budgets": budgets,
        "runs": demo.RECENT_RUNS,
        "chips": demo.HEALTH_CHIPS,
        "ranking": ranking_view(params.get("sel"), params),
    }


# ---------------------------------------------------------------------------
# 12 · Oferty
# ---------------------------------------------------------------------------

TAGS = {
    "ok": ("może dać KUP", "accent"),
    "unknown": ("warunki nieznane", "neutral"),
    "estimated": ("cena szacowana", "neutral"),
}


def offers_view(params: Mapping[str, str | None]) -> View:
    origin = params.get("origin") if params.get("origin") in demo.ORIGINS else None
    qual_only = params.get("qual") == "1"
    rows = sorted(
        (o for o in demo.OFFERS if (origin is None or o.origin == origin) and (not qual_only or o.status == "ok")),
        key=lambda o: o.k,
    )
    return {
        "rows": [
            {
                "o": o,
                "hours": f"{decimal(o.hours)} h",
                "payable": pln(o.payable),
                "adult": pln(o.per_adult),
                "k": pln(o.k),
                "tag": TAGS[o.status][0],
                "tag_kind": TAGS[o.status][1],
            }
            for o in rows
        ],
        "count": len(rows),
        "total": len(demo.OFFERS),
        "chips": [
            {
                "label": "Wszystkie" if c is None else c,
                "on": c == origin,
                "href": href("/oferty", params, origin=c),
            }
            for c in (None, *demo.ORIGINS)
        ],
        "qual_only": qual_only,
        "qual_href": href("/oferty", params, qual=None if qual_only else "1"),
    }


# ---------------------------------------------------------------------------
# 13 · Skany
# ---------------------------------------------------------------------------


def _step(name: str, note: str, t: str, warn: bool = False) -> View:
    return {"name": name, "note": note, "t": t, "warn": warn}


def scans_view(params: Mapping[str, str | None]) -> View:
    scans = demo.SCANS
    sc = next((s for s in scans if s.id == params.get("scan")), scans[0])
    warn = not sc.ok
    is_confirm = sc.mode != "Pełny"
    steps = [
        _step("Blokada i wpis w runs", f"flock · run #{140 + len(scans) - scans.index(sc)}", "0,1 s"),
        _step("Kurs NBP", "USD 3,98 · EUR 4,31 · tabela A z dnia", "0,4 s"),
        _step(
            "Planer",
            f"{sc.queries} zapytań z top 24 h" if is_confirm else "4 lotniska × 12 dat × 4 powroty = 192",
            "0,2 s",
        ),
        _step(
            "Zapytania do dostawców",
            "161 Ignav OK · 31 timeout → fast-flights 30" if warn else f"{sc.queries} wywołań · cache {sc.cache}",
            sc.duration,
            warn,
        ),
        _step(
            "Normalizacja",
            "1 błąd parsowania (fast-flights)" if warn else "ceny grupy w PLN, czasy UTC + lokalne",
            "1,1 s",
        ),
        _step("Ocena", "filtry → kwota do zapłaty → K", "0,6 s"),
        _step(
            "Potwierdzenie spadku",
            "Turkish WAW 21.12 −5,4% · live potwierdzona" if sc.id == "s3" else "brak spadku ≥ 5%",
            "—",
        ),
        _step(
            "Decyzja i alerty",
            "BLISKO wysłane 20:31" if sc.id == "s2" else "bez nowych alertów (deduplikacja)",
            "0,2 s",
        ),
        _step(
            "Zamknięcie i heartbeat",
            f"healthchecks: {'scan_full' if sc.mode == 'Pełny' else 'scan_confirm'} OK",
            "0,3 s",
        ),
    ]
    return {
        "stats": demo.SCAN_STATS,
        "rows": [{"s": s, "selected": s.id == sc.id, "href": href("/skany", params, scan=s.id)} for s in scans],
        "sel": {"when": sc.when, "title": f"{sc.mode} · {sc.queries} zapytań", "steps": steps},
    }


# ---------------------------------------------------------------------------
# 14 · Reguły taryf
# ---------------------------------------------------------------------------

RULE_FIELDS = (
    ("code", "Linia (kod IATA)"),
    ("brand", "Marka taryfy"),
    ("bag", "Bagaż rejestrowany / os."),
    ("carry", "Bagaż podręczny / os."),
    ("seat", "Miejsca obok siebie / os."),
    ("change", "Zmiana daty powrotu"),
    ("refund", "Zwrot"),
)


def rules_view(
    rules: Sequence[FareRule],
    params: Mapping[str, str | None],
    *,
    error: str | None = None,
    form: Mapping[str, str] | None = None,
) -> View:
    have = {r.id for r in rules}
    missing = [m for m in demo.MISSING_RULES if rule_id(m.code, m.brand) not in have]
    sel_id = params.get("rule") or (rules[0].id if rules else None)
    rule = next((r for r in rules if r.id == sel_id), None)
    miss = next((m for m in missing if rule_id(m.code, m.brand) == sel_id), None)
    if rule is not None:
        src: dict[str, str] = {k: getattr(rule, k) for k, _ in RULE_FIELDS} | {"airline": rule.airline}
        kicker, title = "Edycja reguły", f"{rule.airline} · {rule.brand}"
        hint = "Zmiana przelicza kwotę do zapłaty w następnym skanie."
    elif miss is not None:
        src = {"code": miss.code, "brand": miss.brand, "airline": miss.airline}
        kicker, title = "Nowa reguła", f"{miss.airline} · {miss.brand}"
        hint = f"Po zapisaniu {miss.offers_24h} ofert przejdzie ponowną ocenę. Najlepsza może dać KUP."
    else:
        src, kicker, title, hint = {}, "Nowa reguła", "Nowa reguła taryfy", "Uzupełnij wszystkie pola."
    if form:
        src = {**src, **form}
    return {
        "missing": [
            {
                "m": m,
                "count": f"{m.offers_24h} {plural(m.offers_24h, 'oferta', 'oferty', 'ofert')} w 24 h",
                "best": pln(m.best),
                "href": href("/reguly", {}, rule=rule_id(m.code, m.brand)) + "#rule-form",
            }
            for m in missing
        ],
        "rows": [
            {"r": r, "selected": r.id == sel_id, "href": href("/reguly", {}, rule=r.id) + "#rule-form"} for r in rules
        ],
        "form": {
            "kicker": kicker,
            "title": title,
            "hint": hint,
            "airline": src.get("airline", ""),
            "fields": [{"name": k, "label": label, "value": src.get(k, "")} for k, label in RULE_FIELDS],
            "error": error,
        },
        "saved": params.get("saved") == "1",
    }


# ---------------------------------------------------------------------------
# 15 · Konfiguracja
# ---------------------------------------------------------------------------


def config_view() -> View:
    return {
        "hash": demo.CONFIG_HASH,
        "groups": demo.CONFIG_GROUPS,
        "plan": {
            "note": demo.IGNAV_PLAN_NOTE,
            "segments": [
                {"label": label, "value": group(v), "width": f"{w}%", "color": c}
                for label, v, w, c in demo.IGNAV_PLAN_SEGMENTS
            ],
            "spare": group(demo.IGNAV_PLAN_SPARE),
            "limit": group(demo.IGNAV_PLAN_LIMIT),
        },
    }
