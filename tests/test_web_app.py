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
    return TestClient(create_app(fare_rules_path=path, today=date(2026, 11, 4)))


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
    r = client.post("/reguly", data=form, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].startswith("/reguly?rule=TK-ecofly&saved=1")
    page = client.get("/reguly?rule=TK-ecofly&saved=1").text
    assert "Zapisano w fare_rules.yaml." in page
    assert "Edycja reguły" in page
    assert "TK EcoFly</span>" not in page.split("Linia · taryfa")[0]  # zniknęła z brakujących


def test_invalid_rule_returns_form_with_error(client: TestClient) -> None:
    r = client.post("/reguly", data={"code": "TURK", "brand": "EcoFly"})
    assert r.status_code == 422
    assert "Kod IATA linii to 2 znaki" in r.text
    assert 'value="TURK"' in r.text
