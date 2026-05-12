#!/usr/bin/env python3
"""
scrape_exam.py – Szkoła w Chmurze exam scraper v4
Pobiera pełną strukturę egzaminu: treści, dropdowny, obrazy, podpowiedzi,
screenshoty, HAR, HTML. Generuje prompt AI do rozwiązania.
"""

import json
import os
import re
import shutil
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("[!] pip install playwright && playwright install chromium")
    sys.exit(1)

BASE_URL = "https://platforma.szkolawchmurze.org"
VW, VH = 1920, 1080

# ─── Formatting ──────────────────────────────────────────────────────────────


class F:
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    CYAN = "\033[36m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    MAGENTA = "\033[35m"
    RESET = "\033[0m"
    CHECK = "+"
    CROSS = "x"
    ARROW = ">"
    DOT = "*"
    PIPE = "|"
    DASH = "-"


def header(text):
    w = 62
    print(f"\n{F.BOLD}{'=' * w}{F.RESET}")
    print(f"{F.BOLD}  {text}{F.RESET}")
    print(f"{F.BOLD}{'=' * w}{F.RESET}")


def section(text):
    print(f"\n{F.CYAN}{F.BOLD}--- {text} ---{F.RESET}")


def info(key, val):
    print(f"  {F.DIM}{key:<16}{F.RESET} {val}")


def ok(msg):
    print(f"  {F.GREEN}[{F.CHECK}]{F.RESET} {msg}")


def warn(msg):
    print(f"  {F.YELLOW}[!]{F.RESET} {msg}")


def err(msg):
    print(f"  {F.RED}[{F.CROSS}]{F.RESET} {msg}")


def task_header(num, total):
    bar = "=" * 56
    print(f"\n{F.MAGENTA}{F.BOLD}  [{num:02d}/{total:02d}] Zadanie {num}{F.RESET}")
    print(f"  {F.DIM}{bar}{F.RESET}")


def san(name):
    return re.sub(r"\s+", "-", re.sub(r'[<>:"/\\|?*\n\r]', "", name)).strip("-")[:80]


# ─── Extract task structure from DOM ─────────────────────────────────────────


def extract_structure(page):
    return page.evaluate(r"""() => {
        const body = document.body.innerText || '';
        const lines = body.split('\n').map(l => l.trim()).filter(Boolean);

        // Metadata
        let subject = '', examType = '';
        const names = ['Język Polski','Polski','Matematyka','Fizyka','Chemia','Biologia',
            'Historia','Geografia','Informatyka','Język Angielski','Angielski',
            'Język Niemiecki','Niemiecki','WOS','Przyroda'];
        for (const line of lines.slice(0, 15)) {
            for (const s of names) {
                if (line.includes(s)) { subject = s; break; }
            }
            if (/egzamin/i.test(line)) examType = line;
            if (subject && examType) break;
        }
        // Normalize
        if (subject === 'Polski') subject = 'Język Polski';
        if (subject === 'Angielski') subject = 'Język Angielski';

        // Date from page (rare)
        let examDate = '';
        const dm = body.match(/(\d{1,2}[\.\/-]\d{1,2}[\.\/-]\d{2,4})/);
        if (dm) examDate = dm[1];

        // Tasks
        const allEls = Array.from(document.querySelectorAll('*'));
        const taskHeaders = allEls.filter(el => {
            const t = el.innerText?.trim();
            return t && /^Zadanie \d+$/.test(t) && el.children.length === 0;
        });

        const tasks = [];
        for (let ti = 0; ti < taskHeaders.length; ti++) {
            const hdr = taskHeaders[ti];
            const num = parseInt(hdr.innerText.match(/\d+/)[0]);

            let container = hdr;
            for (let j = 0; j < 10; j++) {
                container = container.parentElement;
                if (!container || container.offsetHeight > 100) break;
            }
            const el = container || hdr.parentElement;

            // Dropdowns
            const dds = [];
            const sels = el ? el.querySelectorAll('mat-select') : [];
            sels.forEach((sel, si) => {
                dds.push({ matSelectId: sel.id || '', index: si });
            });

            // Images
            const imgs = [];
            (el ? el.querySelectorAll('img') : []).forEach((img, ii) => {
                if (img.src && !img.src.startsWith('data:') && img.naturalWidth > 10) {
                    imgs.push({ src: img.src, alt: img.alt || '', index: ii });
                }
            });

            // Text
            let text = el ? el.innerText?.substring(0, 3000) : '';

            // Hint
            const hintBtn = el ? Array.from(el.querySelectorAll('button')).find(
                b => b.innerText.trim() === 'Podpowiedź') : null;

            tasks.push({ num, text, dds, imgs, hasHint: !!hintBtn,
                top: hdr.getBoundingClientRect().top + window.scrollY });
        }

        return { subject, examType, examDate, taskCount: tasks.length, tasks };
    }""")


# ─── Clean KaTeX text ────────────────────────────────────────────────────────


def clean_option_text(raw):
    """Clean KaTeX-rendered text: collapse multi-char math into formula."""
    # Remove excessive whitespace from KaTeX rendering
    cleaned = re.sub(r"\n+", " ", raw)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    return cleaned.strip()


# ─── Process tasks ───────────────────────────────────────────────────────────


def process_tasks(page, out, structure):
    total = structure["taskCount"]
    tasks_data = []

    for task in structure["tasks"]:
        num = task["num"]
        tdir = out / f"Zadanie_{num}"
        tdir.mkdir(exist_ok=True)

        task_header(num, total)

        # Text
        (tdir / "Tresc_zadania.txt").write_text(
            f"ZADANIE {num}\n{'=' * 40}\n\n{task['text']}", encoding="utf-8"
        )
        ok("Treść zadania zapisana")

        # Images
        img_files = []
        for img in task["imgs"]:
            ext = Path(urllib.parse.urlparse(img["src"]).path).suffix or ".png"
            if ext not in [".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp"]:
                ext = ".png"
            fn = f"Zdjecie_{img['index'] + 1}{ext}"
            try:
                r = page.request.get(img["src"])
                if r.ok:
                    (tdir / fn).write_bytes(r.body())
                    img_files.append(fn)
                    ok(f"Zdjęcie zapisane: {fn}")
            except:
                pass

        # Dropdowns
        dd_data = []
        for dd in task["dds"]:
            mid = dd["matSelectId"]
            if not mid:
                continue
            try:
                page.evaluate(f"""() => {{
                    const s = document.getElementById('{mid}');
                    if (s) {{ s.scrollIntoView({{block:'center'}}); s.click(); }}
                }}""")
                page.wait_for_timeout(700)

                options = page.evaluate("""() => {
                    const p = document.querySelector('.mat-mdc-select-panel, .cdk-overlay-pane [role="listbox"]');
                    if (!p) return [];
                    return Array.from(p.querySelectorAll('mat-option')).map(o => {
                        let text = o.innerText.trim();
                        const tc = o.textContent.trim();
                        if (tc.length < text.length) text = tc;
                        return { text: text.replace(/\\n/g, ' ').replace(/\\s{2,}/g, ' ') };
                    });
                }""")

                fn = f"Lista_rozwijana_{dd['index'] + 1}.png"
                page.screenshot(path=str(tdir / fn), full_page=False)

                cleaned_opts = [clean_option_text(o["text"]) for o in options]
                dd_data.append(
                    {
                        "index": dd["index"] + 1,
                        "options": cleaned_opts,
                        "screenshot": fn,
                    }
                )
                opts_str = " | ".join(cleaned_opts)
                ok(f"Lista rozwijana {dd['index'] + 1}: [{opts_str[:65]}]")

                page.evaluate(
                    "() => { document.querySelector('.cdk-overlay-backdrop')?.click() || document.body.click(); }"
                )
                page.wait_for_timeout(400)
            except Exception as e:
                warn(f"Błąd przy liście rozwijanej {dd['index'] + 1}: {str(e)[:60]}")
                try:
                    page.evaluate(
                        "() => document.querySelector('.cdk-overlay-backdrop')?.click()"
                    )
                except:
                    pass
                page.wait_for_timeout(200)

        # Save dropdown options
        if dd_data:
            lines = [f"OPCJE ODPOWIEDZI - Zadanie {num}\n{'=' * 40}\n"]
            for d in dd_data:
                num_opts = [f"[{i + 1}] {opt}" for i, opt in enumerate(d["options"])]
                lines.append(
                    f"  Opcje dla luki nr {d['index']}:  {' | '.join(num_opts)}"
                )
            (tdir / "Opcje_do_wyboru.txt").write_text(
                "\n".join(lines), encoding="utf-8"
            )

        # Hint
        hint_file = None
        if task["hasHint"]:
            try:
                page.evaluate(f"""() => {{
                    const h = Array.from(document.querySelectorAll('*')).find(
                        el => el.innerText?.trim() === 'Zadanie {num}' && el.children.length === 0);
                    if (!h) return;
                    let c = h;
                    for (let j = 0; j < 10; j++) {{ c = c.parentElement; if (!c || c.offsetHeight > 100) break; }}
                    if (!c) return;
                    const btn = Array.from(c.querySelectorAll('button')).find(b => b.innerText.trim() === 'Podpowiedź');
                    if (btn) {{ btn.scrollIntoView({{block:'center'}}); btn.click(); }}
                }}""")
                page.wait_for_timeout(1000)
                page.screenshot(path=str(tdir / "Podpowiedz.png"), full_page=False)
                hint_file = "Podpowiedz.png"
                ok("Zapisano podpowiedź do zadania")
                page.keyboard.press("Escape")
                page.wait_for_timeout(300)
            except Exception as e:
                warn(f"Błąd przy pobieraniu podpowiedzi: {str(e)[:50]}")

        # Screenshot
        try:
            page.evaluate(f"""() => {{
                const h = Array.from(document.querySelectorAll('*')).find(
                    el => el.innerText?.trim() === 'Zadanie {num}' && el.children.length === 0);
                if (h) h.scrollIntoView({{block:'start'}});
            }}""")
            page.wait_for_timeout(500)
            page.screenshot(
                path=str(tdir / "Zrzut_ekranu_zadania.png"), full_page=False
            )
            ok("Zapisano zrzut ekranu zadania")
        except:
            pass

        tasks_data.append(
            {
                "num": num,
                "dropdowns": dd_data,
                "images": img_files,
                "hint": hint_file,
                "text": task["text"][:500],
            }
        )

    return tasks_data


# ─── Screenshots ─────────────────────────────────────────────────────────────


def capture_screenshots(page, out):
    ss_dir = out / "Zrzuty_ekranu_calej_strony"
    ss_dir.mkdir(exist_ok=True)
    files = []
    try:
        info = page.evaluate("""() => {
            const c = document.querySelector('#content');
            if (c && c.scrollHeight > c.clientHeight)
                return {sel:'#content', h:c.scrollHeight, vh:c.clientHeight, custom:true};
            return {sel:null, h:document.documentElement.scrollHeight, vh:window.innerHeight, custom:false};
        }""")
        h, vh = info["h"], info["vh"]
        step = int(vh * 0.85)
        sel, cust = info.get("sel"), info["custom"]
        scmd = (
            (lambda p: f"document.querySelector('{sel}').scrollTop={p}")
            if cust
            else (lambda p: f"window.scrollTo(0,{p})")
        )

        page.evaluate(scmd(0))
        page.wait_for_timeout(400)
        pos, idx = 0, 0
        while pos < h:
            page.evaluate(scmd(pos))
            page.wait_for_timeout(800)
            idx += 1
            fn = f"Fragment_strony_{idx}.png"
            page.screenshot(path=str(ss_dir / fn), full_page=False)
            files.append(fn)
            pos += step
        try:
            page.screenshot(path=str(ss_dir / "Pelna_strona.png"), full_page=True)
            files.append("Pelna_strona.png")
        except:
            pass
    except Exception as e:
        warn(str(e)[:60])
    return files


# ─── AI Prompt ───────────────────────────────────────────────────────────────


def generate_ai_prompt(structure, tasks_data, out):
    subject = structure["subject"] or "Nieznany"
    exam_type = structure["examType"] or "Egzamin"

    prompt_lines = [
        f"# INSTRUKCJA DLA AI: ROZWIĄŻ EGZAMIN",
        f"",
        f"Jesteś ekspertem w dziedzinie: **{subject}**. Twoim celem jest bezbłędne i naturalne rozwiązanie poniższego egzaminu ({exam_type}).",
        f"Dla każdego zadania przeanalizuj dostępne materiały (treść, dostępne opcje do wyboru, zdjęcia i podpowiedzi).",
        f"",
        f"## WYMAGANY FORMAT ODPOWIEDZI",
        f"Odpowiedzi muszą być ABSOLUTNIE JEDNOZNACZNE. Zawsze używaj formatu z numerem opcji (który masz podany w nawiasach kwadratowych obok opcji).",
        f"",
        f"⚠️ BARDZO WAŻNA ZASADA: ⚠️",
        f"1. BEZWZGLĘDNIE ZABRANIAM używania formatowania matematycznego LaTeX (żadnych znaków $, \\frac, \\cdot, itp.). Używaj tylko najzwyklejszych znaków z klawiatury (np. 1/2 zamiast ułamka, 'razy' lub * zamiast kropki). Odpowiedzi mają być proste i czyste, bez dziwnych znaków.",
        f"2. BĄDŹ EKSTREMALNIE DOKŁADNY: Zawsze upewnij się, że przypisany przez Ciebie numer opcji (np. Opcja 3) w 100% odpowiada tekstowi z listy opcji przypisanej do tej luki! Nie wybieraj złego numeru do dobrego tekstu. Nie zmyślaj odpowiedzi – wybieraj TYLKO te podane na liście dla danej luki i weryfikuj poprzez sprawdzenie odpowiedniego zdjęcia.",
        f"3. ZERO HALUCYNACJI: Zawsze wybieraj opcję, która jest na liście i jest zgodna z tekstem. Nie wybieraj opcji, która nie jest na liście ani nie jest zgodna z tekstem. Weryfikuj zawsze odpowiednią opcję na podstawie tekstu z listy i zdjęcia.",
        f"4. UPEWNIAJ SIĘ ŻE WSZYSTKIE OPCJE ZOSTANĄ POPRAWNIE ZAZNACZONE: niektóre zadania mają opcję zaznaczenia wielu odpowiedzi, analizuj je, a w razie czego daj uzytkownikowi informację że jest możliwość zaznaczenia wielu odpowiedzi (jeśli jakieś pasują jeszcze ale nie podałeś ich)",
        f"",
        f"Dla każdego zadania z listami rozwijanymi podaj wybrane opcje dokładnie w tym formacie:",
        f"Luka 1: **Opcja [NUMER]** (Zwykły tekst opcji z listy)  --->  KONTEKST: [Zacytuj fragment zdania przed luką] **[WYBRANA OPCJA]** [Zacytuj fragment zdania po luce]",
        f"Luka 2: **Opcja [NUMER]** (Zwykły tekst opcji z listy)  --->  KONTEKST: [Zacytuj fragment zdania przed luką] **[WYBRANA OPCJA]** [Zacytuj fragment zdania po luce]",
        f"",
        f"Przykład:",
        f"Luka 1: **Opcja 3** (2x + 2)  --->  KONTEKST: Wzór tej funkcji liniowej to f(x) = **2x + 2** dla wszystkich argumentów.",
        f"Luka 2: **Opcja 1** (<)  --->  KONTEKST: Z wykresu odczytujemy, że współczynnik kierunkowy a jest **<** od zera.",
        f"",
        f"To BARDZO WAŻNE: podawanie kontekstu zdania ułatwia odnalezienie luki, zwłaszcza gdy opcja to tylko jeden znak (np. <, >).",
        f"Jeśli masz tabelę Prawda/Fałsz z listami rozwijanymi, jako kontekst po prostu napisz pełne zdanie z tabeli, a jako opcję Prawda lub Fałsz.",
        f"Zawsze na samym początku pogrubiaj NUMER OPCJI (np. **Opcja 2**).",
        f"",
        f"Na końcu podaj krótkie (max 2 zdania) uzasadnienie logiczne (również ZWYKŁYM TEKSTEM, zero LaTeXa!).",
        f"",
        f"---\n",
    ]

    for t in tasks_data:
        prompt_lines.append(f"### ZADANIE {t['num']}")
        prompt_lines.append(f"")

        text_preview = t["text"].replace("\n", " ")[:400]
        prompt_lines.append(f"**Treść:** {text_preview}...")
        prompt_lines.append(f"")

        if t["dropdowns"]:
            prompt_lines.append(
                f"**Dostępne opcje do wyboru (kolejno dla luk w zadaniu):**"
            )
            for dd in t["dropdowns"]:
                num_opts = " | ".join(
                    f"[{i + 1}] {opt}" for i, opt in enumerate(dd["options"])
                )
                prompt_lines.append(f"- Luka nr {dd['index']}: {num_opts}")
            prompt_lines.append(f"")

        if t["images"]:
            prompt_lines.append(
                f"**Dodatkowe materiały graficzne:** {', '.join(t['images'])}"
            )
            prompt_lines.append(f"")

        if t["hint"]:
            prompt_lines.append(f"**Podpowiedź systemowa:** Zobacz plik Podpowiedz.png")
            prompt_lines.append(f"")

        task_path = out / f"Zadanie_{t['num']}"
        prompt_lines.append(
            f"*(Pełne dane znajdziesz w folderze: {task_path.as_posix()}/ )*"
        )
        prompt_lines.append(f"\n---\n")

    return "\n".join(prompt_lines)


# ─── Main ────────────────────────────────────────────────────────────────────


def main():
    header("SZKOLA W CHMURZE  //  EXAM SCRAPER v5")
    print(f"""
  {F.DIM}Instrukcja:{F.RESET}
    1. Otworzy się przeglądarka internetowa
    2. Zaloguj się i otwórz wybrany egzamin
    3. Wróć do tego okna i naciśnij ENTER
""")

    with sync_playwright() as p:
        har_tmp = Path(__file__).parent / "_tmp.har"
        if har_tmp.exists():
            har_tmp.unlink()

        browser = p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
        )
        ctx = browser.new_context(
            no_viewport=True,
            record_har_path=str(har_tmp),
            record_har_url_filter="**/*",
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        )
        page = ctx.new_page()
        page.goto(BASE_URL, timeout=30000)

        input(
            f"  {F.BOLD}{F.ARROW} Naciśnij ENTER, gdy jesteś gotowy(a) na stronie egzaminu...{F.RESET} "
        )

        page.wait_for_timeout(2000)
        url = page.url
        exam_id = (
            re.search(r"/exam/(\d+)", url)
            or type("", (), {"group": lambda s, x: "0"})()
        ).group(1)

        section("ANALIZA DANYCH")
        structure = extract_structure(page)

        subject = structure["subject"]
        exam_type = structure["examType"]
        date_str = structure["examDate"] or datetime.now().strftime("%Y-%m-%d")
        total_dd = sum(len(t["dds"]) for t in structure["tasks"])
        total_img = sum(len(t["imgs"]) for t in structure["tasks"])

        info("Przedmiot", subject or "Nieznany")
        info("Typ egzaminu", exam_type or "Nieznany")
        info("Data", date_str)
        info("Liczba zadań", str(structure["taskCount"]))
        info("Listy rozwijane", str(total_dd))
        info("Ilość zdjęć", str(total_img))

        # Output dir
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        dir_name = f"{san(subject or 'Egzamin')}_{san(exam_type or 'Test')}_ID{exam_id}_{date_str.replace('.', '-')}_{ts}"
        out = Path(__file__).parent / "wyniki" / dir_name
        out.mkdir(parents=True, exist_ok=True)

        section("ZAPISYWANIE DANYCH")

        # HTML
        (out / "Zrodlo_strony").mkdir(exist_ok=True)
        (out / "Zrodlo_strony" / "Pelny_kod_strony.html").write_text(
            page.content(), encoding="utf-8"
        )
        (out / "Zrodlo_strony" / "Sam_tekst_ze_strony.txt").write_text(
            page.evaluate("() => document.body.innerText"), encoding="utf-8"
        )
        ok("Zapisano źródło HTML oraz sam tekst")

        # Per-task
        section("PRZETWARZANIE ZADAŃ")
        tasks_data = process_tasks(page, out, structure)

        # Screenshots
        section("ZRZUTY EKRANU CAŁEJ STRONY")
        screenshots = capture_screenshots(page, out)
        ok(f"Wykonano zrzuty ekranu całej strony ({len(screenshots)} plików)")

        # HAR
        section("RUCH SIECIOWY (HAR)")
        (out / "Zapis_ruchu_sieciowego_HAR").mkdir(exist_ok=True)
        har_out = out / "Zapis_ruchu_sieciowego_HAR" / "Ruch_sieciowy.har"
        if har_tmp.exists():
            try:
                shutil.copy(har_tmp, har_out)
                ok(
                    f"Ruch sieciowy zabezpieczony (pełny zapis nastąpi po zamknięciu skryptu: {har_out.stat().st_size / 1024:.0f} KB)"
                )
            except:
                pass

        # Metadata
        meta = {
            "subject": subject,
            "exam_type": exam_type,
            "date": date_str,
            "task_count": structure["taskCount"],
            "url": url,
            "exam_id": exam_id,
            "scraped_at": datetime.now().isoformat(),
            "tasks": tasks_data,
            "screenshots": screenshots,
        }
        (out / "Metadane_techniczne.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        ok("Zapisano metadane techniczne")

        # AI Prompt
        section("GENEROWANIE PROMPTU AI")
        prompt = generate_ai_prompt(structure, tasks_data, out)
        (out / "PROMPT_DLA_AI.md").write_text(prompt, encoding="utf-8")
        ok("Zapisano gotowy prompt dla modelu AI: PROMPT_DLA_AI.md")

        # README
        task_lines = []
        for t in tasks_data:
            parts = []
            if t["dropdowns"]:
                parts.append(f"{len(t['dropdowns'])} luk do wypełnienia")
            if t["images"]:
                parts.append(f"{len(t['images'])} zdjęć")
            if t["hint"]:
                parts.append("jest podpowiedź")
            extra = f"  ({', '.join(parts)})" if parts else ""
            preview = t["text"].replace("\n", " ")[:50]
            task_lines.append(f"  Zadanie {t['num']:02d}: {preview}...{extra}")

        (out / "INFORMACJE_O_EGZAMINIE.md").write_text(
            f"""# {subject or "Egzamin"} – {exam_type or "Test"}

| Informacja | Wartość |
|------------|---------|
| Przedmiot | {subject or "?"} |
| Typ | {exam_type or "?"} |
| Data | {date_str} |
| Ilość zadań | {structure["taskCount"]} |
| List rozwijanych | {total_dd} |
| Ilość obrazów | {total_img} |
| Link do egzaminu | {url} |
| Data archiwizacji | {meta["scraped_at"]} |

## Struktura folderów

```
{out.name}/
{"".join(chr(10) + "  " + f"Zadanie_{t["num"]}/" for t in tasks_data)}
  Zrzuty_ekranu_calej_strony/
  Zrodlo_strony/
  Zapis_ruchu_sieciowego_HAR/
  PROMPT_DLA_AI.md
  INFORMACJE_O_EGZAMINIE.md
  Metadane_techniczne.json
```

## Opis Zadań
{chr(10).join(task_lines)}

## Co znajduje się w folderze każdego zadania?
| Plik | Opis |
|------|------|
| `Tresc_zadania.txt` | Pełna treść i instrukcja do zadania |
| `Opcje_do_wyboru.txt` | Lista ukrytych opcji z list rozwijanych |
| `Lista_rozwijana_X.png` | Zrzut ekranu otwartej listy wyboru |
| `Zdjecie_X.ext` | Obrazy i grafiki użyte w zadaniu |
| `Podpowiedz.png` | Zrzut ekranu oficjalnej podpowiedzi do zadania |
| `Zrzut_ekranu_zadania.png` | Podgląd całego zadania |

## Jak uzyskać odpowiedzi?
Otwórz plik `PROMPT_DLA_AI.md` i wklej jego treść do ChatGPT / Claude / Gemini. Został on przygotowany tak, by AI podało intuicyjne i estetyczne odpowiedzi.
""",
            encoding="utf-8",
        )
        ok("Zapisano podsumowanie: INFORMACJE_O_EGZAMINIE.md")

        # Summary
        header("PODSUMOWANIE PROCESU")
        info("Folder z wynikami", str(out))
        info("Zarchiwizowanych zadań", str(len(tasks_data)))
        info("Zapisanych opcji", str(total_dd))
        info("Pobranych zdjęć", str(total_img))
        info("Gotowy prompt dla AI", "PROMPT_DLA_AI.md")
        print()

        print(
            f"\n{F.GREEN}{F.BOLD} [>] GOTOWE! Egzamin zarchiwizowany pomyślnie. [<]{F.RESET}\n"
        )
        print(f"{F.RED}{F.BOLD} [!] WAŻNE [!]{F.RESET}")
        print(
            f"{F.RED} NIE WYŁĄCZAJ tego terminala ani NIE KLIKAJ CTRL+C, dopóki nie ukończysz{F.RESET}"
        )
        print(
            f"{F.RED} egzaminu i nie zobaczysz swojego wyniku. Jeśli to zrobisz, przeglądarka{F.RESET}"
        )
        print(f"{F.RED} z egzaminem natychmiast się zamknie!{F.RESET}")
        print(
            f"\n{F.DIM} (Zostaw to okno w tle. Po skończonym egzaminie po prostu zamknij przeglądarkę.){F.RESET}\n"
        )

        import time

        from playwright.sync_api import Error as PlaywrightError

        try:
            while True:
                # Sprawdzamy czy strona nadal istnieje
                if page.is_closed():
                    break
                time.sleep(1)
        except (KeyboardInterrupt, PlaywrightError, Exception):
            pass

        print("\nZamykanie i zapisywanie ostatecznych plików...")

        # Zapisz pełny HAR po zamknięciu
        if har_tmp.exists():
            try:
                shutil.copy(har_tmp, har_out)
            except:
                pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
