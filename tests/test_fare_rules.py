from datetime import date
from pathlib import Path

import pytest

from flightwatch.fare_rules import FareRule, FareRuleError, FareRuleStore


def test_upsert_roundtrip_and_replace(tmp_path: Path) -> None:
    store = FareRuleStore(tmp_path / "data" / "fare_rules.yaml")
    assert store.load() == []
    store.upsert(FareRule("tk", "Turkish Airlines", " EcoFly ", bag="1×23 kg"), date(2026, 11, 4))
    store.upsert(FareRule("TK", "Turkish Airlines", "EcoFly", bag="1×30 kg"), date(2026, 11, 5))
    rules = store.load()
    assert len(rules) == 1
    assert rules[0].code == "TK" and rules[0].brand == "EcoFly"
    assert rules[0].bag == "1×30 kg" and rules[0].updated == "5.11"
    assert "Turkish Airlines" in (tmp_path / "data" / "fare_rules.yaml").read_text(encoding="utf-8")


@pytest.mark.parametrize("code,brand", [("TKX", "EcoFly"), ("", "EcoFly"), ("TK", " ")])
def test_validation(tmp_path: Path, code: str, brand: str) -> None:
    with pytest.raises(FareRuleError):
        FareRuleStore(tmp_path / "r.yaml").upsert(FareRule(code, "x", brand), date(2026, 11, 4))


def test_seed_file_loads() -> None:
    rules = FareRuleStore(Path(__file__).parent.parent / "data" / "fare_rules.yaml").load()
    assert {r.id for r in rules} >= {"QR-economy-classic", "EK-economy-flex", "EY-economy-value"}
    assert all(r.complete for r in rules)
