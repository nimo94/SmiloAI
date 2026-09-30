@echo off
echo ==============================================================
echo Building Optimized SmiloAI Executable (Windows)
echo ==============================================================

echo Cleaning up previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist SmiloAI.spec del /q SmiloAI.spec

echo.
echo Launching PyInstaller Compilation Process...
echo This will take several minutes. Do NOT close this window.
echo.

:: PyInstaller flags:
:: --noconfirm: overwrite existing
:: --onedir: creates a folder with .exe and dependencies (faster launch, less RAM)
:: --windowed: hides console window on launch
:: --icon: sets the app icon
:: --add-data: includes static files
:: --hidden-import: forces inclusion of dynamic AI libraries
:: --exclude-module: strips unused modules to save space

pyinstaller --noconfirm ^
    --name "SmiloAI" ^
    --onedir ^
    --windowed ^
    --icon "logo.ico" ^
    --add-data "index.html;." ^
    --add-data "logo.png;." ^
    --add-data "chart.js;." ^
    --add-data "AUTOPILOT/logo.png;AUTOPILOT" ^
    --hidden-import "uvicorn.logging" ^
    --hidden-import "uvicorn.loops" ^
    --hidden-import "uvicorn.loops.auto" ^
    --hidden-import "uvicorn.protocols" ^
    --hidden-import "uvicorn.protocols.http" ^
    --hidden-import "uvicorn.protocols.http.auto" ^
    --hidden-import "uvicorn.protocols.websockets" ^
    --hidden-import "uvicorn.protocols.websockets.auto" ^
    --hidden-import "uvicorn.lifespan" ^
    --hidden-import "uvicorn.lifespan.on" ^
    --hidden-import "fastapi" ^
    --hidden-import "requests" ^
    --hidden-import "ultralytics" ^
    --hidden-import "onnxruntime" ^
    --exclude-module "tkinter" ^
    --exclude-module "PyQt5" ^
    --exclude-module "PySide2" ^
    main_closed.py

echo.
if exist "dist\SmiloAI\SmiloAI.exe" (
    echo ==============================================================
    echo SUCCESS! SmiloAI has been successfully compiled!
    echo Your optimized application is located in the "dist\SmiloAI" folder.
    echo Double-click SmiloAI.exe to launch the app locally!
    echo ==============================================================
) else (
    echo ==============================================================
    echo BUILD FAILED! Check the error logs above.
    echo ==============================================================
)
pause
