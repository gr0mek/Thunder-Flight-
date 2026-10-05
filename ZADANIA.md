# FlightWatch – zadania dla Ciebie

Stan na 5.10.2026. Start zbierania danych: **11.10** · termin decyzji zakupowej: **15.11** (ostrzeżenie TERMIN 8.11).
Kod robi Claude w PR [#1](https://github.com/gr0mek/Thunder-Flight-/pull/1). Tu jest tylko to, czego nie da się zrobić bez Ciebie.

> **Zasada:** klucze, tokeny i hasła wpisujesz w panelu (**Ustawienia**), w `.env` na serwerze albo w ustawieniach środowiska Claude.
> Nigdy nie wklejaj ich do czatu, do issue ani do repo.

---

## 0. Decyzje ze specu §9 (zapisane 5.10)

| # | Pytanie | Twoja odpowiedź | Skutek |
|---|---|---|---|
| 1 | Zawęzić MVP do WAW/KRK/GDN/BER i biletu w obie strony? | **Nie – więcej opcji w MVP** | do MVP wchodzą warianty z sesji 6 → więcej zapytań API i więcej pracy przed startem (patrz 1.1–1.3) |
| 2 | Skan warstwowy (rano pełny, wieczorem top 20)? | **Tak** | zostaje ADR-004 |
| 3 | Nocleg w hubie wliczać do kwoty do zapłaty przy osobnych biletach? | **Tak** | nocleg liczy się do progu 11 000 zł; Claude zmieni definicję w `CLAUDE.md` (zasada 2), w specu §5 i doda nowy ADR |

---

## 1. Decyzje do podjęcia teraz (≈ 15 min)

### 1.1 Które dodatkowe opcje mają być w MVP?
Zaznacz to, co ma działać przed 15.11:

- [ ] **Dolot tanią linią** – wylot na Bali z VIE / PRG / BUD, dolot z WMI (lub dojazd)
- [ ] **Osobne bilety przez huby** – np. WAW→IST + IST→DPS (huby: IST, DOH, DXB, AUH, SIN, KUL, BKK), z noclegiem w hubie
- [ ] **Warianty elastyczności** – `roundtrip_mixed_fare` (tania taryfa tam, elastyczna z powrotem) i `two_oneways_flex_return` (2 bilety w jedną stronę)
- [ ] **Open-jaw** – powrót do innego lotniska niż wylot (wpisz, które: ________)
- [ ] **Monitor po zakupie** – cotygodniowe dopłaty za zmianę daty powrotu (ekran 10 jest już zaprojektowany)

### 1.2 Budżet zapytań Ignav
Obecny plan: 8 000/mies. (≈ 16 USD) i już teraz jest wykorzystany w ~95% przez sam podstawowy skan (192 zapytania rano + 20 wieczorem).
Szacunek (do weryfikacji w sesji 0) przy wszystkich opcjach z 1.1, liczonych codziennie:

| Część skanu | Zapytań / dzień |
|---|---|
| podstawowy: 4 lotniska × 12 dat × 4 powroty | 192 |
| wylot z VIE / PRG / BUD | +144 |
| dolot tanią linią (odcinki do VIE / PRG / BUD) | +48 |
| 2 bilety w jedną stronę | +112 |
| osobne bilety przez 4 huby dalekiego zasięgu | +450 |
| **razem** | **≈ 950 (≈ 28 000 / mies.)** |

Jeśli spike pokaże, że Ignav przyjmuje kilka lotnisk w jednym zapytaniu, liczby mocno spadną. Wybierz:

- [ ] **A.** Większy plan Ignav (≈ 30 000/mies., szacunkowo ≈ 60 USD/mies.)
- [ ] **B.** Rozszerzenia co 2–3 dni, podstawowy skan codziennie (≈ 14–16 tys./mies.) – **rekomendacja Claude**, do czasu wyniku spike'u
- [ ] **C.** Zostać przy 8 000 i zmniejszyć siatkę (np. 6 dat wylotu zamiast 12)

### 1.3 Start 11.10 przy większym zakresie
- [ ] **Etapami (rekomendacja):** 11.10 rusza podstawowy skan (dane od pierwszego dnia), rozszerzenia dochodzą ok. 18.10 – nadal ~4 tygodnie danych przed 15.11
- [ ] **Wszystko naraz:** start zbierania przesuwa się, aż wszystkie opcje będą gotowe

---

## 2. Konta i klucze (≈ 45 min)

Gdzie wpisać: panel → **Ustawienia** (zapisuje do `.env`), tam też są przyciski testu połączenia.

- [ ] **Ignav** – załóż konto i wygeneruj klucz API → `IGNAV_API_KEY`.
      Sprawdź w dokumentacji: cena dla dziecka (wiek), warunki taryfy, kilka lotnisk w zapytaniu. **Zapisz adres API (host)** – będzie potrzebny w 3.1.
- [ ] **SerpApi** – konto (plan darmowy, 250 wyszukań/mies.), klucz z https://serpapi.com/manage-api-key → `SERPAPI_API_KEY`.
- [ ] **Bot Telegrama**
  1. W Telegramie otwórz [@BotFather](https://t.me/BotFather) → `/newbot` → nazwa → skopiuj token → `TELEGRAM_BOT_TOKEN`.
  2. Napisz `/start` do swojego nowego bota (bez tego bot nie może do Ciebie pisać).
  3. Swój numer czatu weź z [@userinfobot](https://t.me/userinfobot) → `TELEGRAM_CHAT_ID`.
  4. W panelu: **Wyślij wiadomość testową**.
- [ ] **healthchecks.io** – konto i 3 checki (ping URL każdego → panel):

  | Check | Okres | Grace | Zmienna |
  |---|---|---|---|
  | scan-full | 1 dzień | 2 h | `HC_PING_SCAN_FULL` |
  | scan-confirm | 1 dzień | 2 h | `HC_PING_SCAN_CONFIRM` |
  | bot | 1 h | 15 min | `HC_PING_BOT` |

  Ustaw powiadomienia healthchecks na e-mail albo Telegram.
- [ ] **(opcjonalnie) Backblaze B2** na kopie bazy
  - prywatny bucket, np. `flightwatch-backup`;
  - klucz aplikacji tylko do tego bucketu → `B2_ACCOUNT_ID`, `B2_ACCOUNT_KEY`;
  - `RESTIC_REPOSITORY=b2:flightwatch-backup:db`;
  - `RESTIC_PASSWORD` – długie hasło, **zapisz je też w menedżerze haseł** (bez niego kopii nie odtworzysz).

---

## 3. Żeby Claude mógł zrobić sesję 0 (spike) – do 6.10

Spike to jednorazowe skrypty, które wyślą kilka prawdziwych zapytań i zapiszą odpowiedzi jako dane testowe. Wybierz jedną drogę:

- [ ] **3.1 W chmurze Claude (zalecane):** menu środowiska w pasku tytułu sesji → **Edit**:
  - **Environment variables:** `IGNAV_API_KEY`, `SERPAPI_API_KEY` (nowa sesja je wczyta);
  - **Network access → Custom → Allowed domains:** host API Ignav (z 2.), `serpapi.com`, `api.nbp.pl`, `api.telegram.org`, `hc-ping.com`.
    Dziś wszystkie te adresy są zablokowane w tym środowisku. Instrukcja: https://code.claude.com/docs/en/cloud-environments#network-access
- [ ] **3.2 U Ciebie:** Claude przygotuje skrypty, a Ty uruchomisz je na laptopie lub VPS (`uv run python scripts/spike_ignav.py`) i wrzucisz wynik z `tests/fixtures/` do repo.

---

## 4. Serwer (do 10.10, przed sesją 5)

- [ ] VPS Ubuntu 24.04, 2 vCPU, 2–4 GB RAM (np. Hetzner CX22)
- [ ] logowanie przez SSH tylko kluczem, bez hasła
- [ ] daj znać, czy wdrożenie robisz sam według instrukcji Claude (`deploy/`), czy Claude ma przygotować jeden skrypt do uruchomienia

Claude nie ma dostępu do Twojego serwera. Wszystkie kroki na serwerze uruchamiasz Ty.

---

## 5. Wartości szacunkowe do sprawdzenia (do 10.10)

W `config.yaml` (oznaczone `SZACUNEK`):

| Wartość | Teraz | Twoja |
|---|---|---|
| wartość godziny podróży (`value_of_hour_pln`) | 30 zł | |
| dojazd WAW (taxi, w obie strony) | 200 zł | |
| dojazd KRK / GDN (pociąg) | 600 zł | |
| dojazd BER (auto / pociąg) | 900 / 1 000 zł | |
| dojazd WMI (taxi) – dla dolotu tanią linią | 400 zł | |
| **nocleg w hubie, pokój rodzinny** – teraz wchodzi do kwoty do zapłaty | 400 zł | |
| ryzyko spóźnienia na osobny bilet (`miss_probability`) | 10% | |
| opłata za miejsce w tanich liniach / os. | 40 zł | |
| wiek dziecka w dniu wylotu | 4 | |

W `data/fare_rules.yaml` (panel → **Reguły taryf**):

- [ ] sprawdź na stronach linii bagaż, miejsca i zmianę daty: QR Economy Classic, EK Economy Flex, EK Economy Saver, LH Economy Classic, SQ Economy Standard, EY Economy Value
- [ ] dodaj brakujące: **TK EcoFly**, **KL Economy Light** (bez nich te oferty nie mogą dać KUP)

---

## 6. Repo i przegląd

- [ ] Zgoda, żeby Claude przeniósł do repo `config.yaml`, `CLAUDE.md`, `PLAN_SESJI.md` i katalog `.10x/` z paczki `flightwatch-10x-pakiet.zip` (nie ma w nich sekretów)
- [ ] Przejrzyj i zmerguj PR [#1](https://github.com/gr0mek/Thunder-Flight-/pull/1) (interfejs, panel, Ustawienia)

---

## Kiedy Claude czego potrzebuje

| Sesja | Kiedy | Od Ciebie |
|---|---|---|
| S1 Szkielet | od razu | punkt 6 (zgoda na pliki w repo) |
| S0 Spike | 6.10 | 1.1, 1.2 i klucze Ignav + SerpApi z punktu 3 |
| S2–S3 Dostawcy i silnik | 7–9.10 | 1.3, fare_rules z punktu 5 |
| S4 Alerty i bot | 9–10.10 | bot Telegrama działa (test w panelu) |
| S5 Serwer | 10.10 | VPS, healthchecks, (B2), wartości z punktu 5 |
| Start | 11.10 | – |
