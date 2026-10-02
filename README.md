<p align="center">
  <img src="docs/images/forestly-logo.png" width="112" alt="Logo Forestly">
</p>

<h1 align="center">MIETEK v2 <sub>by FORESTLY</sub></h1>

<p align="center">
  <b>Edytor taksacji leśnej</b><br>
  Rejestr, opisy taksacyjne i wydruki MIETKA — w przeglądarce, bez MS-DOS.<br>
  <sub>Część ekosystemu <a href="https://github.com/wskakuj/FORESTLY">Forestly</a></sub>
</p>

<p align="center">
  <img alt="Platforma" src="https://img.shields.io/badge/platform-Windows%2010%2F11-blue">
  <img alt="Python" src="https://img.shields.io/badge/python-3.10%2B-3776ab">
  <img alt="Motyw" src="https://img.shields.io/badge/motyw-ciemny%20%2F%20jasny-2dd4a7">
</p>

---

## Co to jest

**MIETEK v2 by FORESTLY** to nowoczesny edytor danych taksacyjnych, który czyta i zapisuje
pliki MIETKA (`.DBF`, słowniki `.LST`) i generuje wydruki zgodne z oryginałem — ale w
interfejsie webowym, w szacie graficznej Forestly („Aurora Glass", motyw ciemny i jasny).

Wszystko działa **lokalnie** — żadnych kont, chmur ani wysyłania danych. Pliki zostają
na Twoim komputerze.

## Funkcje

| | Funkcja |
|---|---|
| **Edytor taksacji** | Opis `OP_TAX` w siatce 7 × 35 znaków, kafelki (drzewostan, zwarcie, podszyt…), podgląd zapisu i wydruku |
| **Rejestr W/D** | Czytelniejsza tabela + panel edycji wybranego rekordu, sortowanie/filtrowanie, aktywny wiersz, regulacja szerokości kolumn |
| **Wydruki MIETKA** | Osiem wydruków 1:1 z oryginałem: OPTAX, REJESTR, ZEST, HALIZNY, TAB_KLW, WSKAZ, WSK_ZB, WYK_NEG — podgląd + zapis `.TXT` (CP852) |
| **Druk HTML** | Jeden wspólny dokument dla podglądu/eksportu/druku, wybór formatu i orientacji oraz marginesów (mm), reset ustawień, eksport `.html` |
| **Zapis do DBF** | ZIP z nadpisanymi `.DBF` oraz kopiami `.BAK` |
| **Dane wsi** | Edycja rekordu `WSIE` z polami daty |

## Jak uruchomić

**Najprościej (bez instalacji):** dwuklik na `uruchom.bat` — otwiera aplikację w przeglądarce.

**Natywne okno (EXE):** uruchom `zrob_repo.bat` — utworzy repo na GitHubie, uruchomi
budowę w GitHub Actions i pobierze `MIETEK v2 by FORESTLY.exe` do folderu `dist\`.
Wymaga jednorazowo:

```bat
winget install --id GitHub.cli
gh auth login
```

**Budowa lokalna:** `build.bat` (wymaga Pythona 3.10+).

## Co sprawdzić ręcznie po zmianach

1. **Pusty start** — po uruchomieniu aplikacja startuje bez danych demo.
2. **Import folderu** — wybierz folder nadrzędny z podfolderami i plikami `.dbf/.DBF`; aplikacja ma wykryć zestawy rekurencyjnie.
3. **Kolizje nazw DBF** — gdy są 2 zestawy z tymi samymi nazwami plików, aplikacja pyta o wybór zestawu po ścieżce.
4. **Rejestr (W/D)** — filtrowanie/sortowanie, aktywny wiersz, panel edycji rekordu, działanie w małym oknie i dla pustej tabeli.
5. **Wydruki HTML** — zmiana marginesów/orientacji/formatu odświeża podgląd; eksport `.html` i druk korzystają z tych samych ustawień.
6. **WebView2/pywebview** — jeśli podgląd/druk natywny jest ograniczony, użyj przycisku „Otwórz lokalny HTML” i drukuj z przeglądarki.

## Struktura

```
MIETEK-v2/
├─ app/main.py              # launcher okienkowy (pywebview)
├─ webapp/index.html        # cała aplikacja (self-contained, offline)
├─ forestly.ico             # ikona (spójna z Forestly)
├─ zrob_repo.bat            # repo + budowa EXE na GitHub Actions
├─ build.bat                # budowa EXE lokalnie
└─ uruchom.bat              # szybkie uruchomienie w przeglądarce
```

## Licencja

Prywatna — część ekosystemu Forestly.
