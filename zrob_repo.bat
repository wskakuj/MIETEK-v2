@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo ============================================================
echo   MIETEK v2 by FORESTLY  -  repo na GitHubie + plik EXE
echo ============================================================
echo.

where git >nul 2>nul || (echo [BLAD] Brak "git" w PATH. Zainstaluj Git for Windows. & pause & exit /b 1)
where gh  >nul 2>nul || (
  echo [BLAD] Brak GitHub CLI ^(gh^).
  echo   Zainstaluj:  winget install --id GitHub.cli
  echo   Potem raz:   gh auth login
  pause & exit /b 1
)
gh auth status >nul 2>nul || gh auth login

set "REPO=MIETEK-v2"
set /p REPO=Podaj nazwe repo na GitHubie [MIETEK-v2]: 

echo.
echo [1/3] Przygotowanie i wyslanie plikow...
if not exist ".git" git init -b main >nul
git add -A
git -c user.email=mietek@forestly.local -c user.name="MIETEK v2" commit -m "MIETEK v2 by FORESTLY" >nul 2>nul

gh repo create "%REPO%" --public --source=. --remote=origin --push
if errorlevel 1 (
  echo     Repo prawdopodobnie juz istnieje - wysylam zmiany...
  git remote remove origin >nul 2>nul
  for /f "delims=" %%u in ('gh api user --jq .login 2^>nul') do set "GHUSER=%%u"
  git remote add origin "https://github.com/%GHUSER%/%REPO%.git"
  git push -u origin main || git push -u origin master
)

echo.
echo [2/3] Uruchamiam budowe EXE w GitHub Actions...
gh workflow run build.yml >nul 2>nul || echo     (workflow wystartuje sam po wyslaniu plikow)

echo.
echo [3/3] Czekam na wynik i pobieram EXE...
timeout /t 20 >nul
gh run watch --exit-status >nul 2>nul
mkdir dist >nul 2>nul
gh run download -n MIETEK-v2-by-FORESTLY -D dist >nul 2>nul

echo.
if exist "dist\MIETEK v2 by FORESTLY.exe" (
  echo ============================================================
  echo   GOTOWE!  Plik:  dist\MIETEK v2 by FORESTLY.exe
  echo ============================================================
) else (
  echo Budowa jeszcze trwa albo trzeba pobrac recznie:
  echo   GitHub -^> zakladka Actions -^> ostatni run -^> Artifacts
  echo   (albo uruchom ten plik ponownie za minute)
)
echo.
pause
