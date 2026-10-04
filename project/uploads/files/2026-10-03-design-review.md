# Przegląd projektu przed developmentem – FlightWatch

**Data:** 2026-10-03
**Zakres:** `config.yaml`, `CLAUDE.md`, `PLAN_SESJI.md`, dokumenty architektury i planu agentów z poprzednich sesji
**Wynik:** projekt gotowy do startu po rozwiązaniu 3 problemów WYSOKICH (wszystkie mają proponowane rozwiązanie)

## Ustalenia

| # | Waga | Problem | Rozwiązanie | Gdzie |
|---|------|---------|-------------|-------|
| 1 | WYSOKIE | **Budżet Ignav się nie domyka.** 2 pełne skany dziennie × 8 lotnisk × 12 dat wylotu × 4 próbki powrotu = 768 zapytań/dzień ≈ 23 000/mies. przy budżecie 8 000. | Skan warstwowy: rano pełna siatka dla 4 lotnisk (192), wieczorem potwierdzenie top 20 + rezerwa 15% na spadki i KUP. ≈ 6 400/mies. + rezerwa do 1 200. | ADR-004, `config.yaml → planner` |
| 2 | WYSOKIE | **Możliwości Ignav niezweryfikowane:** ceny z dzieckiem, warunki taryfy (zmiana/zwrot), wiele lotnisk w jednym zapytaniu, link do rezerwacji. Od tego zależy cały MVP. | Sesja 0 (spike, ok. 1 h): prawdziwe zapytanie WAW→DPS 2+1, zapis odpowiedzi jako fixture, tabela „jest / nie ma”. Bramka przed sesją 2. | EM, plan sesji |
| 3 | WYSOKIE | **Brak źródła danych o bagażu i miejscach obok siebie.** Kwota do zapłaty (próg 11 000 zł) wymaga tych kwot, a API lotów ich zwykle nie zwraca. | Ręcznie utrzymywany plik `data/fare_rules.yaml` (linia + marka taryfy → bagaż w cenie, opłata za miejsce, zmiana, zwrot). Brak reguły = oferta oznaczona „koszt dodatkowy nieznany” i nie może wywołać KUP. | ADR-003, DBA |
| 4 | ŚREDNIE | **WMI jako lotnisko wylotu.** Z Modlina nie ma lotów długodystansowych; ma sens tylko jako dolot tanią linią (sesja 6). | WMI przeniesione do `feeder_origins`. | config |
| 5 | ŚREDNIE | **VIE/PRG/BUD mają koszt dojazdu `null`.** Bez dolotu nie da się policzyć K. | W MVP poza siatką; wracają w sesji 6 razem z logiką dolotu. | config, PM |
| 6 | ŚREDNIE | **Reguła „mistake fare” bez minimalnej próby.** Pierwsza obserwacja ma medianę = sobie, kolejne mogą fałszywie odpalić alert. | Wymagane ≥ 7 dni danych live. | config |
| 7 | ŚREDNIE | **Klucz SerpApi idzie w adresie URL** (`?api_key=`). Logi httpx na poziomie INFO zapisują adres → klucz w logach. | Filtr redagujący sekrety w loggerze + test. | Security |
| 8 | ŚREDNIE | **Bot Telegrama bez listy dozwolonych czatów.** Każdy, kto znajdzie bota, może wywołać `/kupione`. | Obsługa komend tylko z `TELEGRAM_CHAT_ID`. | Security |
| 9 | ŚREDNIE | **Zmiana czasu 28.03.2027** wypada w oknie powrotu (15–31.03). Błąd strefy = zły filtr nocnego przylotu. | Wszystko w UTC, konwersja przez `zoneinfo` na brzegach, test z datą 28.03. | Staff, QA |
| 10 | ŚREDNIE | **Nieznane warunki zmiany daty.** Nie wiadomo, czy traktować ofertę jako elastyczną. | Nieznane = nieelastyczne (kara 1 000 zł w rankingu) + etykieta „warunki nieznane” w alercie. | ADR-003 |
| 11 | ŚREDNIE | **Skan i bot piszą do SQLite jednocześnie.** Ryzyko `database is locked`. | Tryb WAL, `busy_timeout=5000`, blokada `flock` na skany. | DBA, DevOps |
| 12 | NISKIE | Wariant „dwa bilety w jedną stronę z elastycznym powrotem” podwaja liczbę zapytań. | MVP: tylko bilet w obie strony + warunki taryfy. Pozostałe warianty w sesji 6. | PM |
| 13 | NISKIE | Nocleg w hubie przy osobnych biletach jest realnym wydatkiem, a nie wchodzi do kwoty do zapłaty. | Do decyzji przy sesji 6 (pytanie otwarte nr 3). | PM |
| 14 | NISKIE | Wylot 31.12 przylatuje 1.01. Nie jest opisane, do której daty odnosi się `date_from/date_to`. | `outbound.date_*` = data wylotu; okno przylotu liczone w lokalnym czasie DPS bez względu na datę. | Spec |
| 15 | NISKIE | Próg 11 000 zł za 3 osoby w szczycie świątecznym może się nie pojawić. | Mechanizm TERMIN (8.11) już to łapie. Po tygodniu danych porównać medianę z progiem. | PM |

## Co jest dobre i zostaje bez zmian
- Rozdzielenie *kwoty do zapłaty* (decyzja) od *kosztu efektywnego K* (ranking).
- Wymóg świeżej ceny live i linku przed KUP.
- Konfiguracja jako jedyne źródło wartości, sekrety tylko w `.env`.
- Wymienne źródła danych z kolejką awaryjną i logowaniem kosztu.
- Proste reguły zamiast ML.
