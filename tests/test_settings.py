import stat
from pathlib import Path

import httpx
import pytest

from flightwatch import checks, settings

TOKEN = "123456789:AAH" + "x" * 32


def test_env_update_preserves_comments_and_unknown_keys(tmp_path: Path) -> None:
    p = tmp_path / ".env"
    p.write_text("# moje\nOTHER=1\nIGNAV_API_KEY=old\n", encoding="utf-8")
    env = settings.EnvFile(p)
    env.update({"IGNAV_API_KEY": "new-key-0123456789", "TELEGRAM_CHAT_ID": "424242"})
    text = p.read_text(encoding="utf-8")
    assert text.startswith("# moje\nOTHER=1\nIGNAV_API_KEY=new-key-0123456789\n")
    assert "TELEGRAM_CHAT_ID=42" in text
    assert env.read()["OTHER"] == "1"
    env.update({"OTHER": None})
    assert "OTHER" not in env.read()


def test_env_file_is_private(tmp_path: Path) -> None:
    env = settings.EnvFile(tmp_path / ".env")
    env.update({"TELEGRAM_CHAT_ID": "424242"})
    assert stat.S_IMODE(env.path.stat().st_mode) == 0o600
    assert env.private()


def test_values_with_special_chars_are_quoted_and_round_trip(tmp_path: Path) -> None:
    env = settings.EnvFile(tmp_path / ".env")
    env.update({"RESTIC_PASSWORD": "pass word #1 $x"})
    assert "RESTIC_PASSWORD='pass word #1 $x'" in env.path.read_text(encoding="utf-8")
    assert env.read()["RESTIC_PASSWORD"] == "pass word #1 $x"


@pytest.mark.parametrize("bad", ["a\nB=1", "it's"])
def test_injection_rejected(tmp_path: Path, bad: str) -> None:
    with pytest.raises(settings.SettingsError):
        settings.EnvFile(tmp_path / ".env").update({"RESTIC_PASSWORD": bad})


def test_apply_form_validates_and_keeps_empty_secrets(tmp_path: Path) -> None:
    env = settings.EnvFile(tmp_path / ".env")
    env.update({"TELEGRAM_BOT_TOKEN": TOKEN})
    changes, errors = settings.apply_form(env, "telegram", {"TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": "abc"})
    assert errors == {"TELEGRAM_CHAT_ID": "Chat ID to liczba (dla grup ujemna)"}
    assert changes == {}
    changes, errors = settings.apply_form(env, "telegram", {"TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": "-1001"})
    assert errors == {}
    assert env.read() == {"TELEGRAM_BOT_TOKEN": TOKEN, "TELEGRAM_CHAT_ID": "-1001"}
    settings.apply_form(env, "telegram", {}, clear=["TELEGRAM_BOT_TOKEN"])
    assert "TELEGRAM_BOT_TOKEN" not in env.read()


def test_apply_form_ignores_other_groups(tmp_path: Path) -> None:
    env = settings.EnvFile(tmp_path / ".env")
    settings.apply_form(env, "telegram", {"IGNAV_API_KEY": "x" * 20, "TELEGRAM_CHAT_ID": "424242"})
    assert env.read() == {"TELEGRAM_CHAT_ID": "424242"}


def test_mask() -> None:
    assert settings.mask("abcdefghijkl1234", secret=True) == "••••1234"
    assert settings.mask("short", secret=True) == "••••"
    assert settings.mask("424242", secret=False) == "424242"


def test_env_example_in_sync_with_registry(tmp_path: Path) -> None:
    out = tmp_path / ".env.example"
    settings.write_example(out)
    assert out.read_text(encoding="utf-8") == (Path(__file__).parent.parent / ".env.example").read_text(
        encoding="utf-8"
    )


def test_file_checks(tmp_path: Path) -> None:
    cfg = tmp_path / "config.yaml"
    env = settings.EnvFile(tmp_path / ".env")
    res = {c.label: c.ok for c in settings.file_checks(env, cfg, 0, tmp_path)}
    assert res == {"config.yaml": False, "Reguły taryf": False, "Plik .env": False, "Katalog danych": True}
    cfg.write_text("a: [1", encoding="utf-8")
    assert not settings.file_checks(env, cfg, 1, tmp_path)[0].ok
    cfg.write_text("a: 1\n", encoding="utf-8")
    assert settings.file_checks(env, cfg, 1, tmp_path)[0].ok


# --- testy połączeń -----------------------------------------------------------


def _client(handler: object) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))  # type: ignore[arg-type]


def test_telegram_get_me_and_send() -> None:
    sent = []

    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/getMe"):
            return httpx.Response(200, json={"ok": True, "result": {"username": "fw_bot"}})
        sent.append(req.read())
        return httpx.Response(200, json={"ok": True})

    env = {"TELEGRAM_BOT_TOKEN": TOKEN, "TELEGRAM_CHAT_ID": "424242"}
    assert checks.telegram(env, _client(handler)) == checks.Result(True, "Token poprawny · bot @fw_bot.")
    assert checks.telegram(env, _client(handler), send_test=True).ok
    assert b'"chat_id":"424242"' in sent[0]


def test_telegram_errors_never_leak_token() -> None:
    def boom(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"cannot reach {req.url}")

    r = checks.telegram({"TELEGRAM_BOT_TOKEN": TOKEN}, _client(boom))
    assert not r.ok and TOKEN not in r.message and "•••" in r.message


def test_telegram_chat_not_found_hint() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        if req.url.path.endswith("/getMe"):
            return httpx.Response(200, json={"ok": True, "result": {"username": "fw_bot"}})
        return httpx.Response(400, json={"ok": False, "description": "Bad Request: chat not found"})

    r = checks.telegram({"TELEGRAM_BOT_TOKEN": TOKEN, "TELEGRAM_CHAT_ID": "424242"}, _client(handler), send_test=True)
    assert not r.ok and "/start" in r.message


def test_serpapi_account() -> None:
    key = "k" * 64

    def handler(req: httpx.Request) -> httpx.Response:
        assert req.url.path == "/account.json"
        return httpx.Response(200, json={"plan_name": "Free Plan", "plan_searches_left": 241})

    r = checks.serpapi({"SERPAPI_API_KEY": key}, _client(handler))
    assert r == checks.Result(True, "Klucz poprawny · Free Plan · pozostało 241 wyszukań w tym miesiącu.")


def test_serpapi_invalid_key() -> None:
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "Invalid API key."})

    assert not checks.serpapi({"SERPAPI_API_KEY": "k" * 64}, _client(handler)).ok


def test_healthchecks() -> None:
    env = {k: f"https://hc-ping.com/{k}" for k in checks.HC_KEYS}

    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(404 if req.url.path.endswith("BOT") else 200)

    r = checks.healthchecks(env, _client(handler))
    assert r == checks.Result(False, "Nie odpowiada: HC_PING_BOT.")
    assert checks.healthchecks({}, _client(handler)).message.startswith("Brak adresów")
