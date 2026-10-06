"""Ustawienia środowiska: klucze API i adresy usług w `.env` (nigdy w repo ani w config.yaml).

Rejestr `SETTINGS` jest jedynym opisem zmiennych: z niego powstaje formularz w panelu,
`.env.example` i lista gotowości do startu.
"""

from __future__ import annotations

import os
import re
import stat
import tempfile
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_ENV_PATH = Path(".env")
DEFAULT_CONFIG_PATH = Path("config.yaml")

Validator = Callable[[str], str | None]  # zwraca komunikat błędu albo None


class SettingsError(ValueError):
    pass


# ---------------------------------------------------------------------------
# Walidatory
# ---------------------------------------------------------------------------


def _api_key(v: str) -> str | None:
    if len(v) < 16 or re.search(r"\s", v):
        return "Klucz ma co najmniej 16 znaków i bez spacji"
    return None


def _telegram_token(v: str) -> str | None:
    if not re.fullmatch(r"\d{5,}:[A-Za-z0-9_-]{30,}", v):
        return "Token od @BotFather wygląda tak: 123456789:AA…"
    return None


def _chat_id(v: str) -> str | None:
    if not re.fullmatch(r"-?\d{3,}", v):
        return "Chat ID to liczba (dla grup ujemna)"
    return None


def _https_url(v: str) -> str | None:
    if not re.fullmatch(r"https://\S+", v):
        return "Adres musi zaczynać się od https://"
    return None


def _restic_repo(v: str) -> str | None:
    if not re.fullmatch(r"b2:[A-Za-z0-9-]+(:\S*)?", v):
        return "Repozytorium B2: b2:nazwa-bucketu:sciezka"
    return None


def _password(v: str) -> str | None:
    return "Hasło ma co najmniej 12 znaków" if len(v) < 12 else None


def _any(v: str) -> str | None:
    return "Bez spacji" if re.search(r"\s", v) else None


# ---------------------------------------------------------------------------
# Rejestr
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Group:
    id: str
    title: str
    description: str
    test: str | None = None  # nazwa testu połączenia (checks.py)


@dataclass(frozen=True)
class Setting:
    key: str
    group: str
    label: str
    required: bool
    secret: bool
    validate: Validator
    help: str
    link: tuple[str, str] | None = None  # (tekst, url)
    placeholder: str = ""


GROUPS = (
    Group("providers", "Dostawcy danych", "Ceny live i ocena Google. Klucze z kont dostawców.", "serpapi"),
    Group("telegram", "Telegram", "Bot wysyła alerty i odpowiada tylko na jednym czacie.", "telegram"),
    Group("monitoring", "Monitoring", "healthchecks.io: ping po każdym skanie i z bota. Brak pingu = alert.", "hc"),
    Group("backup", "Kopie zapasowe", "Opcjonalne. restic szyfruje bazę i wysyła do Backblaze B2 (03:15)."),
)

SETTINGS = (
    Setting("IGNAV_API_KEY", "providers", "Ignav – klucz API", True, True, _api_key,
            "Główne źródło cen live, 8 000 zapytań/mies.", placeholder="klucz z panelu Ignav"),
    Setting("SERPAPI_API_KEY", "providers", "SerpApi – klucz API", True, True, _api_key,
            "Ocena Google (niska/typowa/wysoka), 250 wyszukań/mies. za darmo.",
            ("serpapi.com/manage-api-key", "https://serpapi.com/manage-api-key")),
    Setting("TRAVELPAYOUTS_TOKEN", "providers", "Travelpayouts – token", False, True, _api_key,
            "Wyłączony w config.yaml – potrzebny dopiero po włączeniu.",
            ("travelpayouts.com", "https://www.travelpayouts.com/")),
    Setting("TELEGRAM_BOT_TOKEN", "telegram", "Token bota", True, True, _telegram_token,
            "Utwórz bota komendą /newbot.", ("@BotFather", "https://t.me/BotFather"),
            placeholder="123456789:AA…"),
    Setting("TELEGRAM_CHAT_ID", "telegram", "Chat ID", True, False, _chat_id,
            "Twój numer czatu. Inne czaty bot ignoruje.", ("@userinfobot", "https://t.me/userinfobot"),
            placeholder="np. 123456789"),
    Setting("HC_PING_SCAN_FULL", "monitoring", "Ping: skan pełny 07:30", True, True, _https_url,
            "Check z okresem 1 dzień.", ("healthchecks.io", "https://healthchecks.io/"),
            placeholder="https://hc-ping.com/…"),
    Setting("HC_PING_SCAN_CONFIRM", "monitoring", "Ping: potwierdzenie 19:30", True, True, _https_url,
            "Check z okresem 1 dzień.", placeholder="https://hc-ping.com/…"),
    Setting("HC_PING_BOT", "monitoring", "Ping: bot", True, True, _https_url,
            "Heartbeat bota, okres 1 h.", placeholder="https://hc-ping.com/…"),
    Setting("RESTIC_REPOSITORY", "backup", "Repozytorium restic", False, False, _restic_repo,
            "Bucket B2 i katalog.", ("Backblaze B2", "https://www.backblaze.com/cloud-storage"),
            placeholder="b2:flightwatch-backup:db"),
    Setting("RESTIC_PASSWORD", "backup", "Hasło szyfrowania", False, True, _password,
            "Zapisz je też poza serwerem – bez niego kopii nie odtworzysz."),
    Setting("B2_ACCOUNT_ID", "backup", "B2 – keyID", False, True, _any, "Klucz aplikacji z dostępem do bucketu."),
    Setting("B2_ACCOUNT_KEY", "backup", "B2 – applicationKey", False, True, _any,
            "Pokazywany raz przy tworzeniu klucza."),
)  # fmt: skip

BY_KEY = {s.key: s for s in SETTINGS}


# ---------------------------------------------------------------------------
# Plik .env
# ---------------------------------------------------------------------------

_LINE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")


def _unquote(raw: str) -> str:
    raw = raw.strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "'\"":
        return raw[1:-1]
    return raw  # jak systemd EnvironmentFile: bez komentarzy w linii


def _quote(v: str) -> str:
    # systemd EnvironmentFile i python-dotenv rozumieją pojedyncze cudzysłowy bez ucieczek
    return f"'{v}'" if re.search(r"[\s#\"$`\\]", v) else v


class EnvFile:
    """Odczyt i zapis `.env` z zachowaniem komentarzy i nieznanych zmiennych. Plik zawsze 600."""

    def __init__(self, path: Path = DEFAULT_ENV_PATH) -> None:
        self.path = path

    def read(self) -> dict[str, str]:
        if not self.path.exists():
            return {}
        out = {}
        for line in self.path.read_text(encoding="utf-8").splitlines():
            m = _LINE.match(line)
            if m and not line.lstrip().startswith("#"):
                out[m.group(1)] = _unquote(m.group(2))
        return out

    def update(self, changes: Mapping[str, str | None]) -> None:
        """Ustawia (str) albo usuwa (None) zmienne; reszta pliku bez zmian."""
        for k, v in changes.items():
            if v is not None and ("\n" in v or "\r" in v or "'" in v):
                raise SettingsError(f"{k}: niedozwolony znak w wartości")
        lines = self.path.read_text(encoding="utf-8").splitlines() if self.path.exists() else []
        pending = dict(changes)
        out = []
        for line in lines:
            m = _LINE.match(line)
            if m and not line.lstrip().startswith("#") and m.group(1) in pending:
                v = pending.pop(m.group(1))
                if v is not None:
                    out.append(f"{m.group(1)}={_quote(v)}")
                continue
            out.append(line)
        if not lines:
            out.append("# FlightWatch – sekrety. Edytowane z panelu (Ustawienia). Nigdy nie commituj.")
        out += [f"{k}={_quote(v)}" for k, v in pending.items() if v is not None]
        self._write("\n".join(out) + "\n")

    def _write(self, text: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".env.", suffix=".tmp")
        try:
            os.fchmod(fd, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(text)
            os.replace(tmp, self.path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    def private(self) -> bool:
        return self.path.exists() and stat.S_IMODE(self.path.stat().st_mode) & 0o077 == 0


def mask(value: str, secret: bool) -> str:
    """Wartość do pokazania w panelu: sekret tylko jako końcówka."""
    if not secret:
        return value
    if len(value) <= 8:
        return "••••"
    return f"••••{value[-4:]}"


def apply_form(
    env: EnvFile, group: str, form: Mapping[str, str], clear: Iterable[str] = ()
) -> tuple[dict[str, str | None], dict[str, str]]:
    """Waliduje pola grupy i zapisuje zmiany. Puste pole sekretu = bez zmian.

    Zwraca (zapisane zmiany, błędy per klucz). Przy błędach nic nie jest zapisywane.
    """
    changes: dict[str, str | None] = {}
    errors: dict[str, str] = {}
    for s in SETTINGS:
        if s.group != group:
            continue
        if s.key in clear:
            changes[s.key] = None
            continue
        v = form.get(s.key, "").strip()
        if not v:
            if not s.secret and s.key in form:
                changes[s.key] = None  # jawne pole wyczyszczone
            continue
        err = s.validate(v)
        if err:
            errors[s.key] = err
        else:
            changes[s.key] = v
    if errors:
        return {}, errors
    if changes:
        env.update(changes)
    return changes, {}


def write_example(path: Path) -> None:
    lines = ["# FlightWatch – zmienne środowiskowe. Skopiuj do .env (chmod 600) albo ustaw w panelu: Ustawienia.", ""]
    for g in GROUPS:
        lines.append(f"# {g.title}")
        for s in SETTINGS:
            if s.group == g.id:
                if not s.required:
                    lines.append("# opcjonalne")
                lines.append(f"{s.key}=")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# Gotowość do startu
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Check:
    label: str
    ok: bool
    detail: str


def file_checks(env: EnvFile, config_path: Path, fare_rules_count: int, data_dir: Path) -> list[Check]:
    checks = []
    if not config_path.exists():
        checks.append(Check("config.yaml", False, f"brak pliku {config_path}"))
    else:
        try:
            yaml.safe_load(config_path.read_text(encoding="utf-8"))
            checks.append(Check("config.yaml", True, f"{config_path} · poprawny YAML"))
        except yaml.YAMLError as e:
            checks.append(Check("config.yaml", False, f"błąd składni: {str(e).splitlines()[0]}"))
    checks.append(Check("Reguły taryf", fare_rules_count > 0, f"{fare_rules_count} w data/fare_rules.yaml"))
    if env.path.exists():
        checks.append(Check("Uprawnienia .env", env.private(), "600" if env.private() else "popraw: chmod 600 .env"))
    else:
        checks.append(Check("Plik .env", False, "powstanie po pierwszym zapisie"))
    writable = data_dir.is_dir() and os.access(data_dir, os.W_OK)
    checks.append(Check("Katalog danych", writable, f"{data_dir}/ " + ("zapisywalny" if writable else "brak zapisu")))
    return checks
