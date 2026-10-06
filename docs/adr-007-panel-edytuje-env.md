# ADR-007: Panel ustawia klucze API i adresy usług w `.env`

**Status:** Proponowany
**Date:** 2026-10-04
**Feature:** flightwatch-mvp

## Context
Przed pierwszym skanem trzeba ustawić 7 wartości (Ignav, SerpApi, token i chat ID bota, 3 pingi
healthchecks) i opcjonalnie 4 dla kopii zapasowych. Ręczna edycja `.env` przez SSH jest podatna na błędy
(literówka w tokenie, brak `https://`, zły chmod) i nic nie mówi, czy klucz działa.

## Decision
- Zakładka **Ustawienia** w panelu zapisuje wyłącznie do `.env` (`FLIGHTWATCH_ENV_FILE`, domyślnie `./.env`).
  `config.yaml` nadal tylko do odczytu, sekrety nigdy w repo (`.env` w `.gitignore`, `.env.example` bez wartości).
- Jeden rejestr zmiennych (`flightwatch/settings.py → SETTINGS`) napędza formularz, walidację,
  `.env.example` (test pilnuje zgodności) i listę „Gotowość do startu”.
- Zapis atomowy, plik zawsze `600`; komentarze i nieznane zmienne zostają. Wartości z nową linią
  lub apostrofem są odrzucane (format zgodny z systemd `EnvironmentFile`).
- Sekret po zapisaniu nie wraca do przeglądarki: widać tylko końcówkę (`••••WXYZ`), puste pole = bez zmian.
- Testy połączeń: Telegram `getMe` + wiadomość testowa, SerpApi Account API (nie zużywa wyszukań),
  ping healthchecks. Ignav bez testu do czasu spike'u (sesja 0). Komunikaty błędów są redagowane.
- Każdy POST w panelu wymaga tokenu CSRF – panel na `127.0.0.1` jest osiągalny z przeglądarki, więc obca
  strona mogłaby inaczej podmienić token bota.

## Consequences
- Zmiany działają po restarcie usług (bot: `systemctl restart fw-bot`; skany przy następnym timerze).
- Panel bez logowania ma teraz możliwość zapisu sekretów – dostęp nadal tylko przez tunel SSH (ADR-006).
