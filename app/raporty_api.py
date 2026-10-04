# -*- coding: utf-8 -*-
"""Wydruki MIETKA w nowym szablonie — HTML i PDF bez Worda.

Tekst wydruku powstaje w przeglądarce (1:1 z oryginalnym MIETKIEM). Ten moduł
zamienia ten sam tekst na estetyczne strony A4, dokładnie tym samym kodem,
którego używa FORESTLY — modułem ``app/szablony.py`` (skopiowanym z FORESTLY,
żeby oba programy dawały identyczny wygląd).

Obsługiwane:
  * osiem wydruków MIETKA (OPTAX, REJESTR1, ZEST1, HALIZNY, TAB_KLW3, WSKAZ1,
    WSK_ZB, WYK_NEG),
  * strona tytułowa (odpowiednik STR_TYT.docx),
  * wykaz skrótów i symboli (z pliku Skroty.docx),
  * dowolny dokument .docx (opisy ogólne) → HTML/PDF.

Wszystko działa lokalnie. PDF powstaje przez wbudowaną przeglądarkę
(Edge/Chrome) w trybie headless — tak samo jak w FORESTLY.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

try:                                    # uruchomienie jako pakiet
    from . import szablony as _sz
except ImportError:                     # uruchomienie jako skrypt (app/ na sys.path)
    import szablony as _sz

# identyfikator wydruku w MIETKU v2 -> typ w module szablonów
TYPY = {
    "optax": "OPTAX",
    "rejestr": "REJESTR1",
    "zest": "ZEST1",
    "halizny": "HALIZNY",
    "tabklw": "TAB_KLW3",
    "wskaz": "WSKAZ1",
    "wskzb": "WSK_ZB",
    "wykneg": "WYK_NEG",
}

# nazwy plików .pdf dla poszczególnych wydruków (jak w FORESTLY)
NAZWY_PDF = {
    "OPTAX": "OPTAX.pdf",
    "REJESTR1": "REJESTR1.pdf",
    "ZEST1": "ZEST1.pdf",
    "HALIZNY": "HALIZNY.pdf",
    "TAB_KLW3": "TAB_KLW3.pdf",
    "WSKAZ1": "WSKAZ1.pdf",
    "WSK_ZB": "WSK_ZB.pdf",
    "WYK_NEG": "WYK_NEG.pdf",
}

# domyślny nagłówek wykonawcy na wydrukach (taki jak w oryginalnym MIETKU)
AGENCJA = "AGENCJA „CEZAR”"


def _base_dir():
    """Katalog zasobów — działa też w EXE spakowanym PyInstallerem."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _assets_dir():
    """Folder z plikami towarzyszącymi (Skroty.docx)."""
    kandydaci = [Path(_base_dir()) / "app" / "assets",
                 Path(__file__).resolve().parent / "assets"]
    for k in kandydaci:
        if k.is_dir():
            return k
    return kandydaci[0]


def _typ(t):
    """'rejestr' / 'REJESTR1' -> 'REJESTR1'."""
    s = str(t or "").strip()
    return TYPY.get(s.lower(), s.upper())


def _marginesy_cm(opcje, typ):
    """Marginesy z ustawień strony MIETKA (mm) na format szablonu (cm).

    Szablon oczekuje gotowej czwórki (góra, prawo, dół, lewo) w centymetrach.
    Gdy użytkownik nic nie ustawił — zwracamy None i zostają domyślne szablonu.
    Pojedynczy bok bez wartości albo z wartością niepoprawną dostaje domyślną
    wartość szablonu (żeby literówka w jednym polu nie rozwaliła wydruku).
    """
    m = (opcje or {}).get("marginesy")
    if not isinstance(m, dict):
        return None
    dom = tuple(getattr(_sz, "_DOMYSLNE_MARGINESY", (1.3, 1.1, 1.5, 1.1)))
    while len(dom) < 4:
        dom = dom + (dom[-1],)
    wart, podane = [], False
    for klucz, domyslna in zip(("top", "right", "bottom", "left"), dom):
        v = m.get(klucz)
        if v is None or v == "":
            wart.append(domyslna)
            continue
        try:
            x = float(str(v).replace(",", ".")) / 10.0
        except (TypeError, ValueError):
            wart.append(domyslna)
            continue
        if x < 0 or x != x:            # ujemne albo NaN
            wart.append(domyslna)
            continue
        wart.append(x)
        podane = True
    if not podane or all(x <= 0 for x in wart):
        return None                    # wszystko zerowe -> domyślne szablonu
    return tuple(wart)


def _html_raportu(typ, tekst, opcje=None):
    """Tekst wydruku MIETKA -> HTML w nowym szablonie."""
    t = _typ(typ)
    renderer = _sz.RENDERERY.get(t)
    if renderer is None:
        raise ValueError("Nieznany wydruk: %s" % (typ,))
    opcje = opcje or {}
    mg = _marginesy_cm(opcje, t)
    # renderery oczekują gotowej czwórki (góra, prawo, dół, lewo) albo None
    if mg is not None and (not isinstance(mg, (tuple, list)) or len(mg) != 4):
        mg = None
    cz = None
    if isinstance(opcje.get("czcionki"), dict):
        cz = opcje["czcionki"].get(t)
    bez = bool(opcje.get("bezNazwisk"))
    nas = opcje.get("nasycenie")

    fd, tmp = tempfile.mkstemp(prefix="mietek-txt-", suffix=".TXT")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(str(tekst or "").encode("cp852", errors="replace"))
        obiekt, stan, okres = _sz.meta_z_pliku(tmp)
        if t == "WSKAZ1":
            return renderer(tmp, obiekt, stan, okres=okres, bez_nazwisk=bez,
                            marginesy=mg, czcionki=cz)
        if t == "WSK_ZB":
            return renderer(tmp, obiekt, okres or stan, bez_nazwisk=bez,
                            marginesy=mg, czcionki=cz)
        if t in ("OPTAX", "REJESTR1"):
            return renderer(tmp, obiekt, stan, bez_nazwisk=bez, marginesy=mg,
                            czcionki=cz, nasycenie_naglowka=nas)
        return renderer(tmp, obiekt, stan, bez_nazwisk=bez, marginesy=mg, czcionki=cz)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _html_na_pdf(html, cel):
    """HTML -> PDF przez Edge/Chrome (headless)."""
    cel = Path(cel)
    cel.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mietek-html-") as tmp:
        hp = Path(tmp) / (cel.stem + ".html")
        hp.write_text(html, encoding="utf-8")
        _sz.html_na_pdf(hp, cel)
    return cel


class RaportyApi:
    """Metody wydruków wystawiane do przeglądarki przez pywebview."""

    # ------------------------------------------------------------ wydruki --
    def raport_nowy(self, typ, txt, opcje=None):
        """Tekst wydruku -> HTML (podgląd i druk w przeglądarce)."""
        try:
            return {"ok": True, "html": _html_raportu(typ, txt, opcje)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def raport_nowy_pdf(self, typ, txt, folder, nazwa=None, opcje=None):
        """Tekst wydruku -> PDF w wybranym folderze."""
        try:
            if not folder:
                return {"ok": False, "error": "Nie wybrano folderu na PDF."}
            t = _typ(typ)
            html = _html_raportu(t, txt, opcje)
            cel = Path(folder) / (nazwa or NAZWY_PDF.get(t, t + ".pdf"))
            _html_na_pdf(html, cel)
            return {"ok": True, "path": str(cel)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def wydruki_nowe_pdf(self, folder, raporty, opcje=None):
        """Wiele wydruków naraz: raporty = [{typ, txt, nazwa}, ...]."""
        pliki, bledy = [], []
        for r in raporty or []:
            r = r or {}
            wynik = self.raport_nowy_pdf(r.get("typ"), r.get("txt"), folder,
                                         r.get("nazwa"), opcje)
            if wynik.get("ok"):
                pliki.append(wynik["path"])
            else:
                bledy.append("%s: %s" % (r.get("nazwa") or r.get("typ"), wynik.get("error")))
        return {"ok": bool(pliki) or not bledy, "files": pliki, "errors": bledy}

    def zabij_pdf(self):
        """Przerywa trwające renderowanie PDF (zamknięcie okna postępu)."""
        try:
            return {"ok": True, "bylo": bool(_sz.zabij_przegladarke())}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ------------------------------------------------------ strona tytułowa --
    def strona_tytulowa(self, dane, opcje=None):
        """Strona tytułowa (odpowiednik STR_TYT.docx) -> HTML."""
        try:
            dane = dane or {}
            with tempfile.TemporaryDirectory(prefix="mietek-tyt-") as tmp:
                p = Path(tmp) / "STR_TYT.html"
                _sz.generuj_str_tyt_html(
                    p,
                    doc_type=dane.get("docType") or "UPUL",
                    prefix=dane.get("prefix") or "",
                    woj=dane.get("woj") or "",
                    powiat=dane.get("powiat") or "",
                    gmina=dane.get("gmina") or "",
                    stan_na=dane.get("stanNa") or "",
                    okres=dane.get("okres") or "",
                    village=dane.get("village") or "NAZWA WSI",
                    agencja=dane.get("agencja") or AGENCJA,
                )
                return {"ok": True, "html": p.read_text(encoding="utf-8")}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def strona_tytulowa_pdf(self, dane, folder, nazwa=None):
        try:
            if not folder:
                return {"ok": False, "error": "Nie wybrano folderu na PDF."}
            wynik = self.strona_tytulowa(dane)
            if not wynik.get("ok"):
                return wynik
            cel = Path(folder) / (nazwa or "STR_TYT.pdf")
            _html_na_pdf(wynik["html"], cel)
            return {"ok": True, "path": str(cel)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ------------------------------------------------------------- skróty --
    def skroty_html(self, opcje=None):
        """Wykaz skrótów i symboli (z Skroty.docx) -> HTML."""
        try:
            docx = _assets_dir() / "Skroty.docx"
            if not docx.exists():
                return {"ok": False, "error": "Brak pliku Skroty.docx w programie."}
            opcje = opcje or {}
            mg = _marginesy_cm(opcje, "SKROTY")
            html = _sz.html_skroty(str(docx), obiekt=opcje.get("obiekt") or "",
                                   stan=opcje.get("stan") or "", marginesy=mg)
            return {"ok": True, "html": html}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def skroty_pdf(self, folder, nazwa=None, opcje=None):
        try:
            if not folder:
                return {"ok": False, "error": "Nie wybrano folderu na PDF."}
            wynik = self.skroty_html(opcje)
            if not wynik.get("ok"):
                return wynik
            cel = Path(folder) / (nazwa or "SKROTY.pdf")
            _html_na_pdf(wynik["html"], cel)
            return {"ok": True, "path": str(cel)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ------------------------------------------------- dokumenty .docx ----
    def wybierz_docx(self):
        """Okno wyboru pliku .docx (opisy ogólne)."""
        try:
            import webview
            kind = getattr(getattr(webview, "FileDialog", None), "OPEN", None) or webview.OPEN_DIALOG
            wybrane = self._window.create_file_dialog(
                kind, directory=self._last_dialog_directory(False),
                allow_multiple=False, file_types=("Dokumenty Word (*.docx)",))
            if not wybrane:
                return {"ok": False, "cancelled": True}
            return {"ok": True, "path": str(Path(wybrane[0]))}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def docx_html(self, sciezka):
        """Dowolny .docx (opis ogólny) -> HTML bez uruchamiania Worda."""
        try:
            if not sciezka or not Path(sciezka).exists():
                return {"ok": False, "error": "Nie znaleziono pliku: %s" % (sciezka,)}
            return {"ok": True, "html": _sz.docx_na_html(str(sciezka))}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def docx_pdf(self, sciezka, folder, nazwa=None):
        try:
            if not folder:
                return {"ok": False, "error": "Nie wybrano folderu na PDF."}
            if not sciezka or not Path(sciezka).exists():
                return {"ok": False, "error": "Nie znaleziono pliku: %s" % (sciezka,)}
            cel = Path(folder) / (nazwa or (Path(sciezka).stem + ".pdf"))
            _sz.docx_na_pdf(str(sciezka), cel)
            return {"ok": True, "path": str(cel)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # -------------------------------------------------------------- folder --
    def wybierz_folder(self, tytul=None):
        """Okno wyboru folderu (np. na PDF-y)."""
        try:
            import webview
            kind = getattr(getattr(webview, "FileDialog", None), "FOLDER", None) or webview.FOLDER_DIALOG
            wybrany = self._window.create_file_dialog(
                kind, directory=self._last_dialog_directory(True))
            if not wybrany:
                return {"ok": False, "cancelled": True}
            return {"ok": True, "folder": str(Path(wybrany[0]))}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def folder_domyslny(self):
        """Propozycja folderu na PDF — tam, gdzie leżą dane, inaczej dokumenty."""
        kandydaci = []
        katalog = getattr(self, "_set_dir", None)
        if katalog:
            kandydaci.append(Path(katalog))
        kandydaci.append(Path.home() / "Documents")
        for k in kandydaci:
            try:
                if k and k.is_dir():
                    return {"ok": True, "folder": str(k)}
            except OSError:
                continue
        return {"ok": True, "folder": ""}

    def przegladarka_pdf(self):
        """Czy jest przeglądarka do robienia PDF (Edge/Chrome)."""
        try:
            exe = _sz.znajdz_przegladarke()
            return {"ok": True, "jest": bool(exe), "sciezka": exe or ""}
        except Exception as e:
            return {"ok": False, "error": str(e)}
