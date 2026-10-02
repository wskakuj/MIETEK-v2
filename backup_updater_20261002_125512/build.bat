@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================================
echo   MIETEK v2 by FORESTLY  -  budowa EXE lokalnie
echo ============================================================
echo   Wymaga: Python 3.10+ w PATH
echo.
python -m pip install --upgrade pip >nul
python -m pip install pyinstaller pywebview pythonnet
echo.
pyinstaller --noconfirm --onefile --windowed --icon "forestly.ico" --name "MIETEK v2 by FORESTLY" --add-data "webapp;webapp" --add-data "docs;docs" --collect-all webview --collect-all clr_loader --hidden-import pythonnet --hidden-import clr app/main.py
echo.
if exist "dist\MIETEK v2 by FORESTLY.exe" (
  echo GOTOWE: dist\MIETEK v2 by FORESTLY.exe
) else (
  echo BLAD budowy - sprawdz komunikaty powyzej.
)
pause
