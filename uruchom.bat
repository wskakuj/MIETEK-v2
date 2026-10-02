@echo off
chcp 65001 >nul
cd /d "%~dp0"

set PY=python
where python >nul 2>nul || set PY=py

%PY% -c "import sys" >nul 2>nul
if errorlevel 1 (
  echo [BLAD] Nie znaleziono Pythona w PATH.
  echo Zainstaluj Python 3.10+ z python.org i zaznacz "Add python.exe to PATH".
  pause
  exit /b 1
)

%PY% -c "import webview" >nul 2>nul
if errorlevel 1 (
  echo Pierwsze uruchomienie - instaluje pywebview i pythonnet...
  %PY% -m pip install --upgrade pip
  %PY% -m pip install pywebview pythonnet
)

echo Uruchamiam MIETEK v2 w oknie programu...
%PY% "%~dp0app\main.py"
if errorlevel 1 (
  echo.
  echo Program zakonczyl sie bledem - sprawdz komunikaty powyzej.
  pause
)
