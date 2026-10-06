# CODING AGENTS: READ THIS FIRST

This is a **handoff bundle** from Claude Design (claude.ai/design).

A user mocked up designs in HTML/CSS/JS using an AI design tool, then exported this bundle so a coding agent can implement the designs for real.

## What you should do — IMPORTANT

**Read the chat transcripts first.** There are 1 chat transcript(s) in `chats/`. The transcripts show the full back-and-forth between the user and the design assistant — they tell you **what the user actually wants** and **where they landed** after iterating. Don't skip them. The final HTML files are the output, but the chat is where the intent lives.

**Read `project/FlightWatch UI.dc.html` in full.** The user had this file open when they triggered the handoff, so it's almost certainly the primary design they want built. Read it top to bottom — don't skim. Then **follow its imports**: open every file it pulls in (shared components, CSS, scripts) so you understand how the pieces fit together before you start implementing.

**If anything is ambiguous, ask the user to confirm before you start implementing.** It's much cheaper to clarify scope up front than to build the wrong thing.

## About the design files

The design medium is **HTML/CSS/JS** — these are prototypes, not production code. Your job is to **recreate them pixel-perfectly** in whatever technology makes sense for the target codebase (React, Vue, native, whatever fits). Match the visual output; don't copy the prototype's internal structure unless it happens to fit.

**Don't render these files in a browser or take screenshots unless the user asks you to.** Everything you need — dimensions, colors, layout rules — is spelled out in the source. Read the HTML and CSS directly; a screenshot won't tell you anything they don't.

## Bundle contents

- `README.md` — this file
- `chats/` — conversation transcripts (read these!)
- `project/` — the `Propozycje UI dla aplikacji` project files (HTML prototypes, assets, components)

---

# Implementacja (gałąź `feat/flightwatch-ui`)

Projekt z `project/FlightWatch UI.dc.html` zbudowany w stacku z `CLAUDE.md` (Python 3.12, uv).

| Część projektu | Kod |
|---|---|
| 01–10 Telegram: alerty, odpowiedzi bota, raporty, 🛠 | `flightwatch/alerts/format.py` – czyste formatery → `Message` (HTML Telegrama + przyciski inline, `to_api()` daje ciało `sendMessage`) |
| Scenariusz z ekranów 01–10 | `flightwatch/alerts/preview.py` (`uv run python -m flightwatch.alerts.preview`) i strona `/telegram` w panelu |
| 11–15 Panel: Przegląd, Oferty, Skany, Reguły taryf, Konfiguracja | `flightwatch/web/` (FastAPI + Jinja, CSS na tokenach Nocturne) – patrz `docs/adr-006-panel-fastapi-jinja.md` |
| Formularz reguł taryf | `flightwatch/fare_rules.py` → `data/fare_rules.yaml` |
| Ustawienia: klucze API, Telegram, healthchecks, kopie B2 + gotowość do startu | `flightwatch/settings.py` → `.env` (600), testy połączeń w `flightwatch/checks.py` – patrz `docs/adr-007-panel-edytuje-env.md` |

```bash
uv sync
uv run flightwatch-panel          # http://127.0.0.1:8080 → Ustawienia
uv run pytest && uv run ruff check . && uv run mypy
```

Panel pokazuje dane przykładowe (`flightwatch/web/demo.py`) do czasu powstania `db/repo.py`.
