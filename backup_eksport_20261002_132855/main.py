# -*- coding: utf-8 -*-
"""
MIETEK v2 by FORESTLY
Launcher okienkowy (pywebview) dla edytora taksacji.

Uruchamia lokalny plik webapp/index.html w natywnym oknie (WebView2 / Edge).
Jeśli pywebview jest niedostępny, otwiera aplikację w domyślnej przeglądarce.

Program jest w pełni lokalny — nic nie wysyła do sieci.
"""
import os
import sys


def base_dir():
    """Katalog zasobów — działa też w EXE spakowanym PyInstallerem (--onefile)."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


APP_TITLE = "MIETEK v2 by FORESTLY"


def index_url():
    root = base_dir()
    index = os.path.join(root, "webapp", "index.html")
    if not os.path.exists(index):
        raise FileNotFoundError("Nie znaleziono pliku: %s" % index)
    return "file:///" + index.replace("\\", "/")


def run_webview():
    import webview  # pywebview

    from db_save_api import DbSaveApi
    api = DbSaveApi()
    api.window = webview.create_window(
        APP_TITLE,
        index_url(),
        width=1560,
        height=980,
        min_size=(1080, 680),
        text_select=True,
        js_api=api,
    )
    webview.start()


def run_browser():
    import webbrowser

    webbrowser.open(index_url())
    print("Otworzono %s w domyślnej przeglądarce." % APP_TITLE)
    print("(Jeśli chcesz natywne okno, zainstaluj: pip install pywebview pythonnet)")


def main():
    try:
        run_webview()
    except Exception as exc:  # brak pywebview / brak WebView2 → przeglądarka
        print("Uwaga: nie udało się otworzyć okna natywnego (%s)." % exc)
        try:
            run_browser()
        except Exception as exc2:
            print("Błąd: %s" % exc2)
            input("Naciśnij Enter, aby zamknąć...")


if __name__ == "__main__":
    main()
