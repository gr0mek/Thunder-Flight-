# Propozycje UI aplikacji

_Started 2026-10-04 10:31 UTC_

---

## User

Przygotuj propozycje UI dla aplikacji

## Assistant



## Assistant

_[tool: read_file]_

_[tool: read_file]_

_[tool: run_script]_

_[tool: run_script]_

_[tool: ask_user]_

Wysłałem formularz z kilkoma pytaniami: które ekrany zaprojektować, ile wariantów, ile treści w alertach i jaki styl wizualny. Zacznę, gdy odpowiesz.

## User

Answered — surface: Wiadomości Telegram (alerty KUP/BLISKO/TERMIN/MISTAKE_FARE), Odpowiedzi bota (/status, /top3, /kupione, /budzet), Raporty dzienny i tygodniowy, Alerty techniczne 🛠, Panel webowy (sesja 6, zamiast/obo…; variations: 1 dopracowany; density: Pełny: + top 3; frame: W ramce telefonu; emoji: Tak, oszczędnie; web_scope: Wykres ceny vs próg i mediana, Siatka dat × lotniska (heatmapa), Ranking ofert z K, Budżet API i zdrowie skanów, Szczegół oferty; design_system: Picked a design system (now attached)

## User

Found issues — fixing…

## User

Found issues — fixing…

## Assistant

_[tool: dc_html_str_replace]_

_[tool: dc_html_str_replace]_

_[tool: ready_for_verification]_

Na ekranie 01 (alert KUP) treść nie mieściła się w telefonie i data przy górnej krawędzi była ucięta. Usunąłem tę datę. Na ekranie 07 skróciłem alert o kursie NBP, żeby pierwsza wiadomość nie dotykała nagłówka. Ponownie uruchomiłem automatyczną kontrolę.

## User

ok, przygotuj reszte brakujacych ekranow

## Assistant

_[tool: grep]_

_[tool: dc_html_str_replace]_

_[tool: dc_html_str_replace]_

_[tool: dc_html_str_replace]_

_[tool: dc_html_str_replace]_

_[tool: dc_js_str_replace]_

_[tool: dc_js_str_replace]_

_[tool: ready_for_verification]_

Dodałem 8 brakujących ekranów do **FlightWatch UI.dc.html**; uruchomiłem automatyczną kontrolę.

**Telegram:**
- **08** – /start z podsumowaniem obserwacji, lista komend i /top3 przed pierwszym skanem („brak danych”).
- **09** – komunikat, że cena z alertu wygasła, oraz ponowny KUP po spadku o co najmniej 3%.
- **10** – po zakupie: cotygodniowe dopłaty za zmianę daty powrotu i alert, że wróciły miejsca.

**Panel webowy** (każdy ekran z aktywną zakładką w nawigacji):
- **11 Przegląd** – dotychczasowy ekran, tylko nowy numer.
- **12 Oferty** – tabela posortowana według K; filtr lotniska i przełącznik „tylko mogące dać KUP” działają.
- **13 Skany** – historia przebiegów i liczniki. Kliknięcie wiersza pokazuje 9 kroków skanu, a przebieg 2.11 pokazuje przejście na fast-flights.
- **14 Reguły taryf** – brakujące reguły, które blokują KUP, tabela fare_rules i formularz. „Dodaj regułę” otwiera pusty formularz.
- **15 Konfiguracja** – podgląd config.yaml w 6 grupach z config_hash i podział budżetu Ignav na miesiąc.

Do decyzji: Konfiguracja tylko pokazuje wartości, żeby config.yaml pozostał jedynym źródłem. Zapis ma tylko formularz reguł taryf. Jeśli panel ma też edytować konfigurację, mogę to dodać.

## User

Found issues — fixing…

## Assistant

_[tool: dc_html_str_replace]_

_[tool: dc_html_str_replace]_

_[tool: dc_html_str_replace]_

_[tool: dc_html_str_replace]_

_[tool: ready_for_verification]_

Na ekranie 08 treść nie mieściła się w telefonie i pierwszy dymek był ucięty pod nagłówkiem. Skróciłem ekran o ponad 60 px:
- usunąłem wiersz „Skany” z powitania;
- połączyłem wylot i powrót w jeden wiersz „Daty”, więc z powitania zniknęły okna godzin przylotu;
- skróciłem opis /budzet i komunikat o braku danych do jednej linii.

Automatyczna kontrola sprawdza poprawkę.

