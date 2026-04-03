@echo off
chcp 850 >nul

echo.
echo ================================================
echo   Build - Radar Survol Conflans-Sainte-Honorine
echo   Generation de l'executable Windows (.exe)
echo ================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python n'est pas installe ou pas dans le PATH.
    echo Telechargez-le sur https://www.python.org/downloads/
    echo Cochez "Add Python to PATH" pendant l'installation !
    pause
    exit /b 1
)

echo [OK] Python detecte :
python --version
echo.

echo [1/3] Installation des dependances...
python -m pip install requests pyinstaller reportlab --quiet
if errorlevel 1 (
    echo [ERREUR] Impossible d'installer les dependances.
    pause
    exit /b 1
)
echo [OK] requests, pyinstaller, reportlab installes
echo.

echo [2/3] Generation du .exe en cours (1-2 minutes)...
echo.
python -m PyInstaller --onefile --windowed --name "RadarSurvolConflans" main.py

if errorlevel 1 (
    echo.
    echo [ERREUR] La generation a echoue.
    pause
    exit /b 1
)

echo.
echo ================================================
echo   [OK] TERMINE !
echo   Votre application : dist\RadarSurvolConflans.exe
echo   Double-cliquez dessus pour la lancer.
echo ================================================
echo.
pause
