# ADR-006: Panel webowy w FastAPI + Jinja zamiast Streamlit

**Status:** Proponowany
**Date:** 2026-10-04
**Feature:** flightwatch-mvp (sesja 6)

## Context
CLAUDE.md przewidywał Streamlit „później”. Projekt UI (`project/FlightWatch UI.dc.html`, Claude Design)
zakłada układ, którego Streamlit nie odtworzy wiernie: siatkę 340 px + wykres, heatmapę dat × lotnisk,
własne tabele z zaznaczaniem wiersza, panel szczegółu i formularz reguł taryf, wszystko na tokenach Nocturne.

## Decision
- FastAPI + Jinja2 renderują HTML po stronie serwera; CSS = `nocturne.css` (design system) + `panel.css`.
- Interakcje (zaznaczenie wiersza, filtr lotniska, przełącznik metryki heatmapy) to zwykłe linki z parametrami
  zapytania – bez JavaScriptu i bez stanu po stronie przeglądarki.
- Panel tylko czyta. Jedyny zapis: formularz reguł taryf → `data/fare_rules.yaml` (zapis atomowy).
  `config.yaml` pozostaje jedynym źródłem konfiguracji.
- Nasłuch na `127.0.0.1:8080`, dostęp przez tunel SSH (jak bot: zero publicznych portów, brak logowania).
- Do czasu `db/repo.py` panel czyta dane przykładowe z `flightwatch/web/demo.py` (scenariusz 4.11.2026).

## Alternatives Considered
| Alternatywa | Zalety | Wady | Dlaczego nie |
|---|---|---|---|
| Streamlit | szybki start, wykresy z pudełka | układ i wygląd poza kontrolą, rerun całego skryptu | nie odda projektu |
| SPA (React/Vite) | bogate interakcje | drugi toolchain (Node), API do utrzymania | za dużo jak na panel 1 osoby |

## Consequences
- Jeden język (Python), testy przez `TestClient`.
- Widoki w `web/views.py` są czystymi funkcjami – po podłączeniu bazy zmienia się tylko źródło danych.
