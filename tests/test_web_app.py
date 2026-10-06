import shutil
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from flightwatch.web.app import create_app

SEED = Path(__file__).parent.parent / "data" / "fare_rules.yaml"


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    path = tmp_path / "fare_rules.yaml"
    shutil.copy(SEED, path)
    return TestClient(
        create_app(
            fare_rules_path=path,
            today=date(2026, 11, 4),
            env_path=tmp_path / ".env",
            config_path=tmp_path / "config.yaml",
        )
    )


@pytest.mark.parametrize(
    "url,needle",
    [
        ("/", "Decyzja dziś"),
        ("/?metric=K&sel=tk", "w granicach 600 zł od najniższego K"),
        ("/oferty?origin=BER", "Emirates"),
        ("/oferty?origin=GDN&qual=1", "2 z 12"),
        ("/skany?scan=s6", "161 Ignav OK"),
        ("/reguly", "Brakujące reguły"),
        ("/konfiguracja", "config_hash 3f9a1c"),
        ("/telegram", "KUP · WAW → DPS"),
        ("/ustawienia", "Gotowość do startu"),
    ],
)
def test_pages_render(client: TestClient, url: str, needle: str) -> None:
    r = client.get(url)
    assert r.status_code == 200
    assert needle in r.text


def test_active_tab_marked(client: TestClient) -> None:
    assert '<a href="/skany" aria-current="page">Skany</a>' in client.get("/skany").text


def test_save_rule_removes_it_from_missing(client: TestClient) -> None:
    form = {
        "code": "TK",
        "brand": "EcoFly",
        "airline": "Turkish Airlines",
        "bag": "1×23 kg",
        "carry": "8 kg",
        "seat": "60 zł/os.",
        "change": "500 zł/os.",
        "refund": "nie",
    }
    r = client.post("/reguly", data={**form, "csrf": client.app.state.csrf}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].startswith("/reguly?rule=TK-ecofly&saved=1")
    page = client.get("/reguly?rule=TK-ecofly&saved=1").text
    assert "Zapisano w fare_rules.yaml." in page
    assert "Edycja reguły" in page
    assert "TK EcoFly</span>" not in page.split("Linia · taryfa")[0]  # zniknęła z brakujących


def test_invalid_rule_returns_form_with_error(client: TestClient) -> None:
    r = client.post("/reguly", data={"code": "TURK", "brand": "EcoFly", "csrf": client.app.state.csrf})
    assert r.status_code == 422
    assert "Kod IATA linii to 2 znaki" in r.text
    assert 'value="TURK"' in r.text


def test_post_without_csrf_is_rejected(client: TestClient) -> None:
    assert client.post("/reguly", data={"code": "TK", "brand": "EcoFly", "csrf": "zly"}).status_code == 403
    assert client.post("/ustawienia", data={"group": "telegram", "TELEGRAM_CHAT_ID": "424242"}).status_code == 403


def test_settings_save_masks_secret_and_updates_readiness(client: TestClient, tmp_path: Path) -> None:
    token = "123456789:AAH" + "x" * 28 + "WXYZ"
    data = {
        "csrf": client.app.state.csrf,
        "group": "telegram",
        "TELEGRAM_BOT_TOKEN": token,
        "TELEGRAM_CHAT_ID": "424242",
    }
    r = client.post("/ustawienia", data=data, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/ustawienia?saved=telegram#g-telegram"
    page = client.get("/ustawienia?saved=telegram").text
    assert token not in page
    assert "••••WXYZ" in page
    assert "Zapisano." in page
    assert "Telegram – token i chat ID" in page
    assert 'value="424242"' in page
    assert "TELEGRAM_BOT_TOKEN=" + token in (tmp_path / ".env").read_text(encoding="utf-8")


def test_settings_invalid_value_shows_error_and_writes_nothing(client: TestClient, tmp_path: Path) -> None:
    data = {"csrf": client.app.state.csrf, "group": "monitoring", "HC_PING_BOT": "http://insecure"}
    r = client.post("/ustawienia", data=data)
    assert r.status_code == 422
    assert "Adres musi zaczynać się od https://" in r.text
    assert not (tmp_path / ".env").exists()


def test_settings_connection_test_uses_injected_client(tmp_path: Path) -> None:
    import httpx

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True, "result": {"username": "fw_bot"}})

    (tmp_path / ".env").write_text("TELEGRAM_BOT_TOKEN=123456789:AAH" + "x" * 32 + "\n", encoding="utf-8")
    app = create_app(
        fare_rules_path=SEED,
        env_path=tmp_path / ".env",
        config_path=tmp_path / "c.yaml",
        http=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    c = TestClient(app)
    r = c.post("/ustawienia/test", data={"csrf": app.state.csrf, "name": "telegram"})
    assert r.status_code == 200
    assert "Token poprawny · bot @fw_bot." in r.text


def test_rejected_form_returns_public_values_but_not_secrets(client: TestClient) -> None:
    data = {
        "csrf": client.app.state.csrf,
        "group": "telegram",
        "TELEGRAM_BOT_TOKEN": "zly-token-sekretny",
        "TELEGRAM_CHAT_ID": "424242",
    }
    r = client.post("/ustawienia", data=data)
    assert r.status_code == 422
    assert 'value="424242"' in r.text
    assert "zly-token-sekretny" not in r.text
