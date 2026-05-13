# 🎓 Szkoła w Chmurze – Exam Scraper

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Playwright](https://img.shields.io/badge/Playwright-Automated-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**Exam Scraper** to potężne, w pełni zautomatyzowane narzędzie stworzone w języku Python z użyciem biblioteki **Playwright**. Służy do bezpiecznego archiwizowania, organizowania i przetwarzania egzaminów z platformy edukacyjnej *Szkoła w Chmurze*.

Narzędzie wykonuje zrzuty ekranu, zrzuca ruch sieciowy (HAR) i inteligentnie wyciąga ukryte opcje z nowoczesnych interfejsów (Angular Material), po czym generuje idealnie skrojony, w 100% zoptymalizowany pod kątem konsolowych asystentów AI (np. `gemini-cli`) tzw. **Prompt**.

---

## 🔥 Kluczowe funkcje

- **Obejście blokad Angular Material:** Skrypt korzysta z niskopoziomowych wstrzyknięć JavaScript (DOM clicks), by omijać niewidzialne blokady kursora (`pointer-events`) i sprawnie przechwytywać treść dynamicznych list rozwijanych (`mat-select`).
- **Inteligentne Screenshoty (Full-Page & Fragmenty):** Narzędzie obchodzi mechanizmy limitujące scrollowanie (`no_viewport`), automatycznie przeskakuje po widoku i łączy wszystko w potężny zrzut `Pelna_strona.png` i pojedyncze fragmenty, dając pewność, że żaden detal nie zostanie ucięty.
- **Archiwizacja ruchu (HAR):** Każdy egzamin generuje plik zapisu ruchu sieciowego, gwarantując bezpieczny zapis sesji.
- **Odporny na błędy (Fail-Safe):** Skrypt jest odporny na złośliwe zjawiska jak błędy wątków Playwright. Nawet wciśnięcie `Ctrl+C` czy nagłe zamknięcie przeglądarki zostało uodpornione na potężne wyjątki (m.in obsługa `TargetClosedError`), co daje niesamowitą czystość w terminalu.
- **AI-Ready Prompting:** Automatycznie generuje niezwykle ustrukturyzowany plik `PROMPT_DLA_AI.md`. Zabrania sztucznej inteligencji "halucynowania" błędnych znaków (twarda blokada języka LaTeX) i formatuje odpowiedzi w konsolowy, brutalnie czytelny sposób, dopisując na sztywno **kontekst** przy każdej opcji.

---

## ⚙️ Wymagania systemowe

Do poprawnego uruchomienia skryptu potrzebujesz:
- Systemu operacyjnego Linux / macOS / Windows
- **Python 3.10** lub nowszego
- Zainstalowanego menedżera pakietów `pip`

---

## 🚀 Instalacja

1. **Pobierz repozytorium** i przejdź do folderu z plikami:
   ```bash
   cd exam_scraper
   ```

2. **Zainstaluj wymagane pakiety Python:**
   Najlepiej zrobić to przez plik `requirements.txt`:
   ```bash
   pip install -r requirements.txt
   ```

3. **Zainstaluj przeglądarkę Playwright:**
   Skrypt opiera się na własnym, wyizolowanym środowisku silnika Chromium. Zainstaluj je komendą:
   ```bash
   playwright install chromium
   ```

---

## 🛠️ Użycie

Uruchomienie skryptu sprowadza się do wywołania jednej komendy w swoim terminalu:

```bash
python3 scrape_exam.py
```

### Flow działania:
1. Skrypt podniesie przeglądarkę i załaduje główną stronę platformy.
2. Zaloguj się ręcznie na swoje konto, podaj PIN i odpal docelowy egzamin, który chcesz rozwiązać.
3. Gdy znajdziesz się na widoku zadań – **zminimalizuj przeglądarkę i wciśnij `ENTER` w terminalu**.
4. Usiądź wygodnie: skrypt w tym momencie przejmuje całkowitą kontrolę nad przeglądarką, odklika wszystko co niezbędne, zrobi dziesiątki zrzutów ekranu i zapisze uporządkowaną strukturę na dysk.
5. Po sekundach skrypt zapali na terminalu jasny status `[>] GOTOWE!`.
6. Zostaw ten terminal w spokoju! Użyj okna obok do skopiowania prompta do `gemini-cli`. Dokończ klikanie swojego egzaminu, a po odebraniu wyników **po prostu zamknij przeglądarkę krzyżykiem**. Skrypt to wykryje, domknie sesję, zapisze log `.har` i kulturalnie odda Ci terminal.

---

## 📂 Struktura Wyników
Wygenerowana struktura:
```text
Wyniki/Chemia_Egzamin_ID31.../
├── Zadanie_1/
│   ├── Tresc_zadania.txt           # Surowy tekst zebrany precyzyjnie ze strony
│   ├── Opcje_do_wyboru.txt         # Opcje zebrane z ukrytych list rozwijanych (ponumerowane z rygorem)
│   ├── Lista_rozwijana_1.png       # Zrzut ekranu momentu rozwinięcia listy
│   ├── Zdjecie_1.png               # Wypięty z HTML i wyizolowany, oryginalny obraz
│   ├── Podpowiedz.png              # Oficjalna podpowiedź w locie uchwycona z tooltipa
│   └── Zrzut_ekranu_zadania.png    # Wizualny dowód całego kontenera z pytaniem
├── Zrodlo_strony/                  # Pełen surowy kod HTML oraz czysty tekst
├── Zrzuty_ekranu_calej_strony/     # Backup płaszczyzny interfejsu podzielony na ułamki scrolla
├── Zapis_ruchu_sieciowego_HAR/     # Kompletny zapis archiwum sieci (na wypadek problemów z połączeniem)
├── PROMPT_DLA_AI.md                # Generowany z automatu, perfekcyjny prompt wejściowy
└── INFORMACJE_O_EGZAMINIE.md       # Czytelne podsumowanie i metadane archiwizacji
```

---

## 🤖 Integracja z AI (`gemini-cli`)

Cały kod pod spodem został wyciśnięty do granic pod kątem spięcia go z aplikacjami odpalanymi na surowych CLI (jak `gemini-cli`).
Otwórz wygenerowany `PROMPT_DLA_AI.md`, rzuć jego zawartością do prompta i obserwuj jak LLM radzi sobie z formatowaniem bez wariowania przy matematyce, rzucając konkretne numerki i dobudowując dla Ciebie czytelny **kontekst**. Zero szukania, zero pomyłek.

---

## ⚖️ Disclaimer i Odpowiedzialność Prawna

**Niniejsze narzędzie zostało stworzone wyłącznie w celach edukacyjnych oraz badawczych (Proof of Concept)**, mających na celu demonstrację mechanizmów automatyzacji i testowania interfejsów webowych.

### Autor repozytorium nie ponosi odpowiedzialności za:

1. **Sposób, w jaki oprogramowanie zostanie wykorzystane przez użytkowników końcowych.**
2. **Naruszenia warunków świadczenia usług (Terms of Service)**, regulaminów platform e-learningowych oraz statutów placówek edukacyjnych.
3. **Konsekwencje dyscyplinarne, prawne lub administracyjne** (np. blokady kont, unieważnienie wyników) wynikające z użycia skryptu.
4. **Ewentualne naruszenia praw autorskich** związane z pobieraniem i archiwizowaniem własności intelektualnej stron trzecich.

### Warunki Użytkowania

Oprogramowanie jest udostępniane **"tak jak jest" (as-is)**, bez żadnych gwarancji. Korzystanie z narzędzia odbywa się na **wyłączne ryzyko użytkownika**.

> ⚠️ **Ważne:** Przed użyciem tego narzędzia zapoznaj się z regulaminem platformy, na której go zamierzasz zastosować. Nieautoryzowana automatyzacja może stanowić naruszenie warunków użytkowania i prawo. Autor nie odpowiada za konsekwencje tego użytku.
