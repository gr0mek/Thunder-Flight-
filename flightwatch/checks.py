"""Testy połączeń z panelu (Ustawienia). Żaden wynik ani błąd nie zawiera wartości sekretów.

Ignav nie ma testu, dopóki spike (sesja 0) nie potwierdzi, które wywołanie nie zużywa budżetu.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

import httpx

TIMEOUT = httpx.Timeout(10.0)


@dataclass(frozen=True)
class Result:
    ok: bool
    message: str


def redact(text: str, secrets: Iterable[str]) -> str:
    for s in secrets:
        if s:
            text = text.replace(s, "•••")
    return text


def _fail(e: Exception, secrets: Iterable[str]) -> Result:
    return Result(False, redact(f"Brak połączenia: {type(e).__name__}: {e}", secrets))


def telegram(env: Mapping[str, str], client: httpx.Client, send_test: bool = False) -> Result:
    """getMe (token) i opcjonalnie wiadomość testowa na TELEGRAM_CHAT_ID."""
    token, chat = env.get("TELEGRAM_BOT_TOKEN", ""), env.get("TELEGRAM_CHAT_ID", "")
    if not token:
        return Result(False, "Najpierw zapisz token bota.")
    base = f"https://api.telegram.org/bot{token}"
    try:
        me = client.get(f"{base}/getMe", timeout=TIMEOUT).json()
        if not me.get("ok"):
            return Result(False, redact(f"Telegram odrzucił token: {me.get('description', 'brak opisu')}", [token]))
        name = "@" + str(me["result"].get("username", "?"))
        if not send_test:
            return Result(True, f"Token poprawny · bot {name}.")
        if not chat:
            return Result(False, f"Token poprawny ({name}), ale brak Chat ID.")
        r = client.post(
            f"{base}/sendMessage",
            json={"chat_id": chat, "text": "✅ FlightWatch: połączenie z panelu działa."},
            timeout=TIMEOUT,
        ).json()
        if not r.get("ok"):
            hint = " Napisz najpierw /start do bota." if "chat not found" in str(r.get("description")) else ""
            return Result(False, redact(f"Wiadomość nie doszła: {r.get('description')}.{hint}", [token]))
        return Result(True, f"Wiadomość testowa wysłana przez {name}.")
    except (httpx.HTTPError, ValueError, KeyError) as e:
        return _fail(e, [token])


def serpapi(env: Mapping[str, str], client: httpx.Client) -> Result:
    """Account API – nie zużywa wyszukań."""
    key = env.get("SERPAPI_API_KEY", "")
    if not key:
        return Result(False, "Najpierw zapisz klucz SerpApi.")
    try:
        r = client.get("https://serpapi.com/account.json", params={"api_key": key}, timeout=TIMEOUT)
        data = r.json()
        if r.status_code != 200 or "error" in data:
            return Result(False, redact(f"SerpApi: {data.get('error', r.status_code)}", [key]))
        left = data.get("plan_searches_left", data.get("total_searches_left"))
        plan = data.get("plan_name", "plan")
        return Result(True, f"Klucz poprawny · {plan} · pozostało {left} wyszukań w tym miesiącu.")
    except (httpx.HTTPError, ValueError) as e:
        return _fail(e, [key])


HC_KEYS = ("HC_PING_SCAN_FULL", "HC_PING_SCAN_CONFIRM", "HC_PING_BOT")


def healthchecks(env: Mapping[str, str], client: httpx.Client) -> Result:
    """Ping każdego checku (oznacza go jako „up” – to zamierzone przy konfiguracji)."""
    urls = {k: env.get(k, "") for k in HC_KEYS}
    missing = [k for k, u in urls.items() if not u]
    if missing:
        return Result(False, "Brak adresów: " + ", ".join(missing) + ".")
    bad = []
    for k, u in urls.items():
        try:
            if client.get(u, timeout=TIMEOUT).status_code != 200:
                bad.append(k)
        except httpx.HTTPError:
            bad.append(k)
    if bad:
        return Result(False, "Nie odpowiada: " + ", ".join(bad) + ".")
    return Result(True, "Wszystkie 3 checki odebrały ping.")
