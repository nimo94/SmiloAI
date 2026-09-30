#!/bin/bash
echo "=============================================================="
echo "Building Optimized SmiloAI Executable (Linux)"
echo "=============================================================="

echo "Cleaning up previous builds..."
rm -rf build dist SmiloAI.spec

echo ""
echo "Launching PyInstaller Compilation Process..."
echo "This will take several minutes."
echo ""

../.venv/bin/python -m PyInstaller --noconfirm \
    --name "SmiloAI" \
    --onedir \
    --windowed \
    --add-data "index.html:." \
    --add-data "logo.png:." \
    --add-data "chart.js:." \
    --add-data "AUTOPILOT/logo.png:AUTOPILOT" \
    --hidden-import "uvicorn.logging" \
    --hidden-import "uvicorn.loops" \
    --hidden-import "uvicorn.loops.auto" \
    --hidden-import "uvicorn.protocols" \
    --hidden-import "uvicorn.protocols.http" \
    --hidden-import "uvicorn.protocols.http.auto" \
    --hidden-import "uvicorn.protocols.websockets" \
    --hidden-import "uvicorn.protocols.websockets.auto" \
    --hidden-import "uvicorn.lifespan" \
    --hidden-import "uvicorn.lifespan.on" \
    --hidden-import "fastapi" \
    --hidden-import "requests" \
    --hidden-import "ultralytics" \
    --hidden-import "onnxruntime" \
    --exclude-module "tkinter" \
    --exclude-module "PyQt5" \
    --exclude-module "PySide2" \
    main_closed.py

echo ""
if [ -f "dist/SmiloAI/SmiloAI" ]; then
    echo "=============================================================="
    echo "SUCCESS! SmiloAI has been successfully compiled!"
    echo "Your optimized application is located in the dist/SmiloAI folder."
    echo "Run ./dist/SmiloAI/SmiloAI to launch the app locally!"
    echo "=============================================================="
else
    echo "=============================================================="
    echo "BUILD FAILED! Check the error logs above."
    echo "=============================================================="
fi
