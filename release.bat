@echo off
chcp 65001 >nul
REM ============================================================
REM  MIETEK v2 by FORESTLY - wydanie nowej wersji (2x klik)
REM ============================================================
cd /d "%~dp0"
python release.py
echo.
pause
