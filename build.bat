@echo off
setlocal
cd /d "%~dp0"

py -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    py -m pip install pyinstaller
    if errorlevel 1 exit /b 1
)

py -m PyInstaller --noconfirm --clean --onefile --noconsole --name Jarvis --distpath dist --workpath build --specpath build --collect-all vosk --collect-all sounddevice --collect-all pygame --collect-all edge_tts --add-data "%~dp0model;model" GUI.py
if errorlevel 1 exit /b 1

echo.
echo Build complete: dist\Jarvis.exe