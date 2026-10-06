"""Ręczne reguły taryf (`data/fare_rules.yaml`): linia + marka taryfy → bagaż, miejsca, warunki.

Panel jest jedynym miejscem zapisu (config.yaml pozostaje tylko do odczytu).
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import asdict, dataclass, fields
from datetime import date
from pathlib import Path

import yaml

DEFAULT_PATH = Path("data/fare_rules.yaml")


@dataclass(frozen=True)
class FareRule:
    code: str  # IATA linii, np. "QR"
    airline: str
    brand: str
    bag: str = ""
    carry: str = ""
    seat: str = ""
    change: str = ""
    refund: str = ""
    updated: str = ""  # "12.10"

    @property
    def id(self) -> str:
        return rule_id(self.code, self.brand)

    @property
    def complete(self) -> bool:
        return all((self.bag, self.carry, self.seat, self.change, self.refund))


def rule_id(code: str, brand: str) -> str:
    return f"{code.strip().upper()}-{'-'.join(brand.lower().split())}"


class FareRuleError(ValueError):
    pass


def validate(rule: FareRule) -> FareRule:
    code = rule.code.strip().upper()
    if not (len(code) == 2 and code.isalnum()):
        raise FareRuleError("Kod IATA linii to 2 znaki, np. QR")
    if not rule.brand.strip():
        raise FareRuleError("Podaj markę taryfy")
    clean = {f.name: str(getattr(rule, f.name)).strip() for f in fields(rule)}
    clean["code"] = code
    return FareRule(**clean)


class FareRuleStore:
    """Plik YAML z listą reguł; zapis atomowy (plik tymczasowy + rename)."""

    def __init__(self, path: Path = DEFAULT_PATH) -> None:
        self.path = path

    def load(self) -> list[FareRule]:
        if not self.path.exists():
            return []
        data = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        known = {f.name for f in fields(FareRule)}
        return [FareRule(**{k: str(v) for k, v in r.items() if k in known}) for r in data.get("rules", [])]

    def get(self, rid: str) -> FareRule | None:
        return next((r for r in self.load() if r.id == rid), None)

    def upsert(self, rule: FareRule, today: date) -> FareRule:
        rule = validate(rule)
        rule = FareRule(**{**asdict(rule), "updated": f"{today.day}.{today.month:02d}"})
        rules = [r for r in self.load() if r.id != rule.id] + [rule]
        self._write(rules)
        return rule

    def _write(self, rules: list[FareRule]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        body = yaml.safe_dump({"rules": [asdict(r) for r in rules]}, allow_unicode=True, sort_keys=False, width=120)
        header = "# Reguły taryf – edytowane z panelu (Reguły taryf). Kwoty za osobę.\n"
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".fare_rules.", suffix=".yaml")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(header + body)
        os.replace(tmp, self.path)
