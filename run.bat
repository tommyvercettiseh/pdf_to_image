@echo off
setlocal
cd /d "%~dp0"

if not exist output mkdir output
if not exist test_files mkdir test_files

python -c "import fitz" >nul 2>&1
if errorlevel 1 (
    echo PyMuPDF ontbreekt. Installeren...
    python -m pip install -r requirements.txt
)

python gui.py

if errorlevel 1 (
    echo.
    echo Er ging iets mis. Druk op een toets om dit venster te sluiten.
    pause >nul
)
