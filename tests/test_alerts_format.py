from dataclasses import replace
from datetime import date, time

import pytest

from flightwatch.alerts import format as f
from flightwatch.alerts import preview


def _plain(text: str) -> str:
    return text.replace(" ", " ")


def test_buy_alert_matches_design_screen_01() -> None:
    msg = preview.screens()[0].items[0]
    assert isinstance(msg, preview.Bot)
    text = _plain(msg.message.text)
    assert text.startswith("<b>🟢 KUP · WAW → DPS</b>\n<b>10 840 zł</b>")
    assert "do zapłaty za 3 os. · 3 980 zł za dorosłego · próg 11 000 zł" in text
    assert "→ wt 22.12 Warszawa 15:55 · śr 23.12 Denpasar 09:30 (18 h 35)" in text
    assert "Zmiana powrotu: 600 zł/os. + różnica taryfy" in text
    assert "2. Najszybsza · BER · 11 510 zł · 36,5 h · 1 przes." in text
    assert "⚠ warunki nieznane" in text
    assert [[b.text for b in row] for row in msg.message.keyboard] == [
        ["Rezerwuj w Qatar ↗"],
        ["Pełne top 3", "Kupione ✓"],
    ]


def test_message_to_api_builds_inline_keyboard() -> None:
    body = f.purchase_confirm("Bali – zima 2026/27").to_api()
    assert body["parse_mode"] == "HTML"
    assert body["reply_markup"] == {
        "inline_keyboard": [
            [
                {"text": "Tak, kupione", "callback_data": "bought:yes"},
                {"text": "Anuluj", "callback_data": "bought:no"},
            ]
        ]
    }


def test_booking_link_must_be_https() -> None:
    o = replace(preview.TK, booking_url="http://example.com")
    with pytest.raises(ValueError, match="https"):
        f.near_alert(o, pax=3, threshold_minor=1_100_000, median_minor=1_205_000, google=None)


def test_dynamic_text_is_html_escaped() -> None:
    w = replace(preview.WATCH, name="<Bali & co>")
    assert "&lt;Bali &amp; co&gt;" in f.purchase_confirm(w.name).text


def test_button_needs_exactly_one_action() -> None:
    with pytest.raises(ValueError):
        f.Button("x")
    with pytest.raises(ValueError):
        f.Button("x", url="https://a", callback="b")


def test_rebuy_shows_drop_and_previous_price() -> None:
    m = f.rebuy_alert(preview._qr(1_050_000, 386_000), pax=3, previous_minor=1_084_000, live_age_min=3)
    text = _plain(m.text)
    assert "🟢 KUP ponownie · −3,1%" in text
    assert "poprzedni KUP 10 840 zł" in text


def test_unknown_change_terms_are_labelled() -> None:
    assert f.ChangeTerms(allowed=None).text() == "nieznane"
    assert f.ChangeTerms(allowed=True).text() == "bezpłatna"
    assert f.ChangeTerms(allowed=False).text() == "niedozwolona"


def test_deadline_alert_pluralises_days() -> None:
    m = f.deadline_alert(
        days_left=1, deadline=date(2026, 11, 15), threshold_minor=1_100_000, options=(), trend_pct=-1.0
    )
    assert "1 dzień do 15.11" in m.text


def test_admin_alerts_carry_prefix() -> None:
    m = f.admin_provider_error(provider="SerpApi", status=401, effect="Ocena Google pominięta.")
    assert m.text.startswith("🛠 <b>SerpApi 401</b>")


def test_no_data_reply() -> None:
    from datetime import datetime

    assert f.no_data_reply(datetime(2026, 10, 11, 7, 30)).text == "Jeszcze brak danych. Pierwszy skan: nd 11.10, 07:30."


def test_every_preview_message_renders() -> None:
    screens = preview.screens()
    assert [s.number for s in screens] == [f"{n:02d}" for n in range(1, 11)]
    for s in screens:
        for it in s.items:
            if isinstance(it, preview.Bot):
                assert it.message.text
                it.message.to_api()


def test_price_expired() -> None:
    m = f.price_expired(
        preview.TK,
        alert_sent_at=time(8, 2),
        now_minor=1_200_000,
        previous_minor=1_118_000,
        next_confirm=time(19, 30),
    )
    assert "(+820 zł)" in _plain(m.text)
