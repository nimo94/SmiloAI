import sys
from typing import List, Dict
import os

# Redirect stdout/stderr to prevent application crash during headless execution
os.environ["PYTHONIOENCODING"] = "utf-8"

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
else:
    try:
        sys.stdout.write("")
    except Exception:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")

if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")
else:
    try:
        sys.stderr.write("")
    except Exception:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")

from fastapi import FastAPI, UploadFile, File, Form, Request, HTTPException, Depends, Header
from fastapi.responses import JSONResponse, StreamingResponse, RedirectResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import cv2
import numpy as np
import base64
from ultralytics import YOLO
import ultralytics

# ✨ User-Added Air-Gap Security: Disable Ultralytics telemetry to prevent network hangs
ultralytics.utils.ONLINE = False

import time
import random
import gc
import torch
import json
from collections import Counter
import traceback
import hashlib
import subprocess
import webbrowser
import threading
from contextlib import asynccontextmanager
from PIL import Image, ImageDraw, ImageFont
import qrcode
import socket
import io
from fastapi.responses import HTMLResponse
import secrets

# Generate a secure session token to lock down the local web server
SESSION_TOKEN = secrets.token_urlsafe(32)
with open(".token", "w") as f:
    f.write(SESSION_TOKEN)
# PyInstaller native splash screen module
try:
    import pyi_splash
except ImportError:
    pyi_splash = None

try:
    import requests
except ImportError:
    print("WARNING: Missing libraries. Run 'pip install requests' to enable Cloud & AI features.")

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

# Load local .env credentials if present (ignored by version control)
for _env_path in (os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")):
    if os.path.exists(_env_path):
        try:
            with open(_env_path, "r", encoding="utf-8") as _f:
                for _line in _f:
                    _line = _line.strip()
                    if _line and not _line.startswith("#") and "=" in _line:
                        _k, _v = _line.split("=", 1)
                        os.environ.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))
        except Exception:
            pass

# Cloud and API configuration (Load from environment or fallback to safe placeholders)
# Cloud Proxy Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
DROPBOX_ACCESS_TOKEN = os.getenv("DROPBOX_ACCESS_TOKEN", "")



# Model state and directories
models = {}
model_colors = {}
MODERN_COLORS = [
    (255, 191, 0), (208, 224, 64), (144, 238, 144),
    (250, 206, 135), (210, 150, 100), (50, 180, 255),
    (230, 216, 173)
]

LOCAL_MODELS_DIR = "model"
AUTOPILOT_OUT_DIR = os.path.join("AUTOPILOT", "AUTOPILOT_MODELS")

os.makedirs(LOCAL_MODELS_DIR, exist_ok=True)
os.makedirs("AUTOPILOT", exist_ok=True)
os.makedirs(AUTOPILOT_OUT_DIR, exist_ok=True)


# Security Helper: Safe Path Resolution to prevent Path Traversal
def safe_model_path(filename: str, base_dir: str = LOCAL_MODELS_DIR) -> tuple[str, str]:
    clean_name = os.path.basename(filename or "")
    if not clean_name or clean_name in (".", "..") or clean_name.startswith("/") or clean_name.startswith("\\"):
        raise ValueError("Invalid model filename provided.")
    target_path = os.path.abspath(os.path.join(base_dir, clean_name))
    abs_base = os.path.abspath(base_dir)
    if not target_path.startswith(abs_base):
        raise ValueError("Security violation: Path traversal detected.")
    return target_path, clean_name


# Security Helper: Verify Authorized / Local Interface Request for Destructive Endpoints
def verify_authorized_request(request: Request, x_api_key: str = Header(None, alias="X-API-Key")):
    configured_key = os.getenv("SMILOAI_SECRET_TOKEN")
    if configured_key:
        if x_api_key != configured_key:
            raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing API token.")
        return
    client_ip = request.client.host if request.client else ""
    if client_ip not in ("127.0.0.1", "localhost", "::1", "testclient"):
        raise HTTPException(status_code=403, detail="Security violation: Unauthenticated destructive actions are restricted to local loopback interface.")


# Application lifespan manager
import platform
import shutil
import webbrowser
import threading

def launch_app_mode(url: str):
    system = platform.system()
    browsers = []

    if system == "Windows":
        browsers = [
            "chrome", "msedge", "opera",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]
        user_data_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "SmiloAI_AppProfile")
    elif system == "Darwin":
        browsers = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ]
        user_data_dir = os.path.expanduser("~/Library/Application Support/SmiloAI_AppProfile")
    else:
        browsers = [
            "google-chrome",
            "google-chrome-stable",
            "chromium-browser",
            "chromium",
            "microsoft-edge",
            "opera"
        ]
        user_data_dir = os.path.expanduser("~/.config/SmiloAI_AppProfile")

    for browser in browsers:
        # Check if browser executable is available in PATH or exists at path
        if shutil.which(browser) or os.path.exists(browser):
            try:
                cmd = [
                    browser, 
                    f"--app={url}", 
                    "--window-size=1440,900",
                    f"--user-data-dir={user_data_dir}",
                    "--no-first-run",
                    "--no-default-browser-check"
                ]
                if system == "Linux":
                    cmd.append("--class=SmiloAI")
                
                process = subprocess.Popen(cmd)
                print(f"Launched SmiloAI App Mode using: {browser}")
                return process
            except Exception as e:
                pass
                
    print("Could not find Chrome/Edge for App Mode. Falling back to default browser.")
    webbrowser.open(url)
    return None

@asynccontextmanager
async def lifespan(app: FastAPI):
    def open_url():
        if os.environ.get("NO_APP_MODE") == "1":
            return
        time.sleep(1.0)
        if pyi_splash and pyi_splash.is_alive():
            pyi_splash.close()

        print("Launching SmiloGui Native App...")
        process = launch_app_mode(f"http://127.0.0.1:8000/?token={SESSION_TOKEN}")
        if process:
            print("Monitoring app window. Close window to shutdown server.")
            process.wait()
            print("App window closed. Shutting down SmiloAI...")
            import signal
            os.kill(os.getpid(), signal.SIGINT)

    threading.Thread(target=open_url, daemon=True).start()

    print("-" * 50)
    print("Scanning local model directory for specialists...")
    local_files = [f for f in os.listdir(LOCAL_MODELS_DIR) if f.endswith(('.pt', '.onnx'))]

    if not local_files:
        if pyi_splash and pyi_splash.is_alive():
            try:
                pyi_splash.update_text("No models found. Proceeding to boot...")
            except Exception:
                pass
        print("No local models found. Awaiting cloud download or manual upload.")
    else:
        for file in local_files:
            file_path = os.path.join(LOCAL_MODELS_DIR, file)
            print(f"Loading {file} into memory...")

            if pyi_splash and pyi_splash.is_alive():
                try:
                    pyi_splash.update_text(f"Loading Specialist: {file}...")
                except Exception:
                    pass

            try:
                models[file] = YOLO(file_path)
                model_colors[file] = random.choice(MODERN_COLORS)
                print(f"Successfully loaded {file}")
            except Exception as e:
                print(f"Failed to load {file}: {e}")

    if pyi_splash and pyi_splash.is_alive():
        try:
            pyi_splash.update_text("Host started. Awaiting browser connection...")
        except Exception:
            pass

    print("-" * 50 + "\n")
    yield


app = FastAPI(title="SmiloAI", version="5.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:5000",
        "http://localhost:5000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    # Public assets that don't need authentication
    if request.url.path in ["/logo.png", "/favicon.ico", "/manifest.json"]:
        return await call_next(request)
        
    token = request.query_params.get("token")
    cookie_token = request.cookies.get("smiloai_session")
    
    is_valid = False
    if token == SESSION_TOKEN:
        is_valid = True
    elif cookie_token == SESSION_TOKEN:
        is_valid = True
        
    if not is_valid:
        return JSONResponse(status_code=403, content={"detail": "Direct browser access is disabled for security. Please use the SmiloAI Desktop Application."})
        
    response = await call_next(request)
    
    # Implicitly log them in via cookie if they authenticated with URL token
    if token == SESSION_TOKEN and cookie_token != SESSION_TOKEN:
        response.set_cookie(key="smiloai_session", value=SESSION_TOKEN, httponly=True, samesite="Lax")
        
    return response


def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


@app.get("/")
async def serve_ui():
    html_path = get_resource_path("index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    return JSONResponse({"status": "error", "message": "UI file not found in executable."})


@app.get("/manifest.json")
async def get_manifest():
    return JSONResponse(content={
        "name": "SmiloAI",
        "short_name": "SmiloAI",
        "start_url": "/",
        "display": "standalone",
        "background_color": "#0f172a",
        "theme_color": "#0f172a",
        "icons": [
            {
                "src": "/logo.png",
                "sizes": "192x192",
                "type": "image/png"
            },
            {
                "src": "/logo.png",
                "sizes": "512x512",
                "type": "image/png"
            }
        ]
    })


@app.get("/logo.png")
async def serve_logo():
    logo_path = get_resource_path("logo.png")
    if os.path.exists(logo_path):
        return FileResponse(logo_path)
    return JSONResponse({"status": "error", "message": "Logo file not found in executable."})


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return RedirectResponse(url="/logo.png")


@app.get("/generate_ai_summary_stream")
async def generate_ai_summary_stream(detections: str, mode: str = "xray"):
    def event_stream():
        if not GROQ_API_KEY:
            yield "data: [ERROR] Valid GROQ_API_KEY required for AI Clinical Assistant.\n\n"
            return

        try:
            scan_context = "an intraoral RGB photograph of a patient's teeth and gums" if mode == "rgb" else "a patient's dental X-Ray"

            prompt = (
                f"You are SmiloAI, a highly advanced clinical dental assistant. The vision engine just scanned {scan_context} "
                f"and detected the following issues: {detections}. "
                f"Write a short, highly professional, but reassuring paragraph (3-4 sentences max) explaining what this means "
                f"and what the standard clinical procedure (like drilling and filling for caries, scaling for calculus, etc.) will be in the clinic. "
                f"Do not use markdown formatting (* or #), just plain readable text."
            )

            import json
            groq_endpoint = "https://api.groq.com/openai/v1/chat/completions"
            headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": "llama3-8b-8192",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.5,
                "max_tokens": 1024,
                "stream": True
            }

            with requests.post(groq_endpoint, headers=headers, json=payload, stream=True) as response:
                if response.status_code != 200:
                    yield f"data: [ERROR] AI Engine failed: {response.text}\n\n"
                    return
                
                for line in response.iter_lines(decode_unicode=True):
                    if line:
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                yield "data: [DONE]\n\n"
                                break
                            try:
                                json_data = json.loads(data_str)
                                if "choices" in json_data and len(json_data["choices"]) > 0:
                                    delta = json_data["choices"][0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        clean_chunk = content.replace('\n', '<br>')
                                        yield f"data: {clean_chunk}\n\n"
                            except Exception:
                                pass

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: [ERROR] {str(e)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


def get_iou(boxA, boxB):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

    iou = interArea / float(boxAArea + boxBArea - interArea + 1e-5)
    return iou


def draw_modern_box_only(master, glow, x1, y1, x2, y2, color):
    overlay = master.copy()
    cv2.rectangle(overlay, (x1, y1), (x2, y2), color, -1)
    cv2.addWeighted(overlay, 0.05, master, 0.95, 0, master)

    L = 20
    T = 1

    corners = [
        ((x1, y1), (x1 + L, y1)), ((x1, y1), (x1, y1 + L)),
        ((x2, y1), (x2 - L, y1)), ((x2, y1), (x2, y1 + L)),
        ((x1, y2), (x1 + L, y2)), ((x1, y2), (x1, y2 - L)),
        ((x2, y2), (x2 - L, y2)), ((x2, y2), (x2, y2 - L))
    ]

    for pt1, pt2 in corners:
        cv2.line(glow, pt1, pt2, color, 3, cv2.LINE_AA)
        cv2.line(master, pt1, pt2, color, T, cv2.LINE_AA)
        cv2.line(master, pt1, pt2, (255, 255, 255), 1, cv2.LINE_AA)


# API endpoint handlers
@app.get("/engine_state")
async def get_engine_state():
    missing_models = []
    for model_name in list(models.keys()):
        file_path = os.path.join(LOCAL_MODELS_DIR, model_name)
        ap_file_path = os.path.join(AUTOPILOT_OUT_DIR, model_name)
        if not os.path.exists(file_path) and not os.path.exists(ap_file_path):
            missing_models.append(model_name)

    for m in missing_models:
        del models[m]
        if m in model_colors:
            del model_colors[m]
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    available_models = []
    try:
        if DROPBOX_ACCESS_TOKEN:
            try:
                import dropbox
            except ImportError:
                print("dropbox module not found. Run pip install dropbox.")
                dropbox = None
            
            if dropbox:
                print("Connecting to Federated Cloud Databanks...")
                dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
                folder_path = '/SmiloAI_Models'
                result = dbx.files_list_folder(folder_path)
                for entry in result.entries:
                    if isinstance(entry, dropbox.files.FileMetadata) and (entry.name.endswith('.onnx') or entry.name.endswith('.pt')):
                        clean_name = entry.name.replace(" ", "_")
                        available_models.append(clean_name)
    except Exception as e:
        print(f"Failed to synchronize federated models via proxy: {e}")

    loaded_models_info = {}
    for name, model in models.items():
        if hasattr(model, 'names'):
            loaded_models_info[name] = list(model.names.values())
        else:
            loaded_models_info[name] = ["Unknown"]

    autopilot_models = []
    autopilot_classes = {}
    if os.path.exists(AUTOPILOT_OUT_DIR):
        for f in os.listdir(AUTOPILOT_OUT_DIR):
            if f.endswith(('.pt', '.onnx')):
                autopilot_models.append(f)
                try:
                    m = YOLO(os.path.join(AUTOPILOT_OUT_DIR, f), task='classify')
                    autopilot_classes[f] = list(m.names.values())
                except Exception:
                    autopilot_classes[f] = []

    return {
        "loaded_models": list(models.keys()),
        "loaded_models_info": loaded_models_info,
        "available_models": available_models,
        "autopilot_models": autopilot_models,
        "autopilot_classes": autopilot_classes
    }


trainer_process = None


@app.post("/launch_trainer")
async def launch_trainer(_auth: None = Depends(verify_authorized_request)):
    global trainer_process

    # ✨ NEW: Forensic Debugger! Writes to console AND a text file!
    def dlog(msg):
        print(f"[DEBUG TRAINER LAUNCH] {msg}")
        try:
            with open("debug_launch_log.txt", "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")
        except Exception:
            pass

    dlog("=== Launch Trainer Request Received ===")

    try:
        if trainer_process is not None:
            dlog(f"Existing trainer_process found. Poll status: {trainer_process.poll()}")
            if trainer_process.poll() is None:
                dlog("Trainer is already running.")
                return {"status": "error", "message": "Training application is already running."}

        current_dir = os.path.abspath(".")
        dlog(f"Current Working Directory: {current_dir}")

        exe_in_autopilot = os.path.join(current_dir, "AUTOPILOT", "auto_pilot_trainer.exe")
        py_in_autopilot = os.path.join(current_dir, "AUTOPILOT", "auto_pilot_trainer.py")
        exe_in_root = os.path.join(current_dir, "auto_pilot_trainer.exe")
        py_in_root = os.path.join(current_dir, "auto_pilot_trainer.py")

        dlog(f"Checking path 1: {exe_in_autopilot} -> Exists? {os.path.exists(exe_in_autopilot)}")
        dlog(f"Checking path 2: {py_in_autopilot} -> Exists? {os.path.exists(py_in_autopilot)}")
        dlog(f"Checking path 3: {exe_in_root} -> Exists? {os.path.exists(exe_in_root)}")
        dlog(f"Checking path 4: {py_in_root} -> Exists? {os.path.exists(py_in_root)}")

        cmd_to_run = None
        cwd_to_use = current_dir

        # ✨ THE CWD FIX: If it's in the AUTOPILOT folder, tell the process its CWD is AUTOPILOT!
        if os.path.exists(exe_in_autopilot):
            cmd_to_run = [exe_in_autopilot]
            cwd_to_use = os.path.dirname(exe_in_autopilot)
        elif os.path.exists(py_in_autopilot):
            cmd_to_run = [os.path.abspath(sys.executable), py_in_autopilot]
            cwd_to_use = os.path.dirname(py_in_autopilot)
        elif os.path.exists(exe_in_root):
            cmd_to_run = [exe_in_root]
        elif os.path.exists(py_in_root):
            cmd_to_run = [os.path.abspath(sys.executable), py_in_root]
        else:
            dlog("No valid executable/script found to launch.")
            return {"status": "error", "message": "Training application not found."}

        dlog(f"Executing CMD: {cmd_to_run}")
        dlog(f"Using CWD: {cwd_to_use}")

        # ✨ THE ULTIMATE FIX: Ask Windows Explorer to launch it, breaking all parent/child bonds!
        if os.name == 'nt' and cmd_to_run[0].endswith('.exe'):
            dlog("Using Windows Shell (os.startfile) to completely decouple the .exe process.")

            old_cwd = os.getcwd()
            try:
                # Temporarily jump into the folder so the .exe feels at home, then launch it
                os.chdir(cwd_to_use)
                os.startfile(cmd_to_run[0])
            finally:
                # Jump back immediately so we don't break FastAPI
                os.chdir(old_cwd)

            dlog("Shell execute triggered successfully.")
            return {"status": "success"}
        else:
            # Fallback for Mac/Linux or raw .py scripts
            kwargs = {"close_fds": True, "start_new_session": True}
            if os.name == 'nt':
                # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_BREAKAWAY_FROM_JOB
                kwargs['creationflags'] = 0x00000008 | 0x00000200 | 0x01000000

            trainer_process = subprocess.Popen(cmd_to_run, cwd=cwd_to_use, **kwargs)
            dlog(f"Subprocess spawned successfully with PID: {trainer_process.pid}")
            return {"status": "success"}

    except Exception as e:
        dlog(f"EXCEPTION CAUGHT: {str(e)}")
        dlog(traceback.format_exc())
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/trainer_status")
async def trainer_status():
    global trainer_process
    is_running = False
    if trainer_process is not None:
        if trainer_process.poll() is None:
            is_running = True
        else:
            trainer_process = None

    return {"is_running": is_running}


@app.get("/get_training_counts")
async def get_training_counts():
    base_dir = os.path.join("AUTOPILOT", "Training_Data")
    counts = {}
    try:
        if os.path.exists(base_dir):
            for d in os.listdir(base_dir):
                cat_path = os.path.join(base_dir, d)
                if os.path.isdir(cat_path):
                    counts[d] = len([f for f in os.listdir(cat_path) if os.path.isfile(os.path.join(cat_path, f))])
        return counts
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/download_cloud_model_stream")
async def download_cloud_model_stream(model_name: str):
    def event_stream():
        try:
            file_path, clean_name = safe_model_path(model_name)
        except ValueError as e:
            yield f"data: ERROR:Security violation - {str(e)}\n\n"
            return
        if clean_name in models:
            yield f"data: ERROR:Model already loaded.\n\n"
            return
        try:
            if DROPBOX_ACCESS_TOKEN:
                try:
                    import dropbox
                except ImportError:
                    yield "data: ERROR:dropbox module not found.\n\n"
                    return
                
                dbx = dropbox.Dropbox(DROPBOX_ACCESS_TOKEN)
                folder_path = '/SmiloAI_Models'
                result = dbx.files_list_folder(folder_path)
                
                target_path = None
                total_size = 0
                for entry in result.entries:
                    if isinstance(entry, dropbox.files.FileMetadata) and entry.name.replace(" ", "_") == clean_name:
                        target_path = entry.path_lower
                        total_size = entry.size
                        break
                        
                if not target_path:
                    yield f"data: ERROR:Model '{clean_name}' not found in cloud databanks.\n\n"
                    return
                    
                _, response = dbx.files_download(target_path)
                downloaded = 0
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                progress = int((downloaded / total_size) * 100)
                                yield f"data: {progress}\n\n"
                            else:
                                yield f"data: 50\n\n"
                
                yield f"data: 100\n\n"
                models[model_name] = YOLO(file_path)
                model_colors[model_name] = random.choice(MODERN_COLORS)
                yield f"data: DONE\n\n"
            else:
                yield f"data: ERROR:DROPBOX_ACCESS_TOKEN not configured.\n\n"
        except Exception as e:
            yield f"data: ERROR:{str(e)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/save_training_data")
async def save_training_data(image: UploadFile = File(...), label: str = Form(...), _auth: None = Depends(verify_authorized_request)):
    try:
        safe_label = "".join([c for c in label if c.isalnum() or c in ['_', '-']]).strip()
        if not safe_label:
            safe_label = "UNLABELED"

        base_dir = os.path.join("AUTOPILOT", "Training_Data")
        label_dir = os.path.join(base_dir, safe_label)
        os.makedirs(label_dir, exist_ok=True)
        contents = await image.read()
        image_hash = hashlib.sha256(contents).hexdigest()
        filename = f"{image_hash}.jpg"
        filepath = os.path.join(label_dir, filename)

        if os.path.exists(base_dir):
            for existing_cat in os.listdir(base_dir):
                cat_path = os.path.join(base_dir, existing_cat)
                if os.path.isdir(cat_path):
                    existing_file = os.path.join(cat_path, filename)
                    if os.path.exists(existing_file):
                        if existing_cat == safe_label:
                            count = len(
                                [f for f in os.listdir(label_dir) if os.path.isfile(os.path.join(label_dir, f))])
                            return {"status": "success", "message": "Duplicate ignored.", "new_count": count}
                        else:
                            os.remove(existing_file)

        with open(filepath, "wb") as f:
            f.write(contents)

        count = len([f for f in os.listdir(label_dir) if os.path.isfile(os.path.join(label_dir, f))])
        return {"status": "success", "message": f"Saved to {filepath}", "new_count": count}
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.post("/load_model")
async def load_model(file: UploadFile = File(...), _auth: None = Depends(verify_authorized_request)):
    try:
        file_path, model_name = safe_model_path(file.filename)
        if model_name in models:
            return JSONResponse({"status": "error", "message": "Model already loaded."})
        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())
        models[model_name] = YOLO(file_path)
        model_colors[model_name] = random.choice(MODERN_COLORS)
        return {"status": "success", "model_name": model_name}
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)})


@app.post("/remove_model")
async def remove_model(model_name: str = Form(...), _auth: None = Depends(verify_authorized_request)):
    try:
        file_path, clean_name = safe_model_path(model_name)
    except ValueError as e:
        return JSONResponse(status_code=400, content={"status": "error", "message": str(e)})
    if clean_name in models:
        del models[clean_name]
        del model_colors[clean_name]
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    return {"status": "success", "message": f"Cleared {clean_name}."}


# ✨ Global Engine Shutdown Endpoint ✨
@app.post("/shutdown")
# ✨ FastApi Bool Fix: Check for exact string "false" just in case the browser sends it wrong
async def shutdown_server(kill_trainer: str = "false", _auth: None = Depends(verify_authorized_request)):
    def kill_process():
        global trainer_process

        should_kill = str(kill_trainer).lower() != "false"

        try:
            with open("debug_launch_log.txt", "a", encoding="utf-8") as f:
                f.write(
                    f"{time.strftime('%Y-%m-%d %H:%M:%S')} - === Shutdown Sequence Initiated (should_kill={should_kill}) ===\n")
        except Exception:
            pass

        # Safely orphan/terminate the trainer if it's running AND we were told to!
        if should_kill and trainer_process is not None and trainer_process.poll() is None:
            try:
                with open("debug_launch_log.txt", "a", encoding="utf-8") as f:
                    f.write(
                        f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Terminating trainer_process (PID: {trainer_process.pid})...\n")
                trainer_process.terminate()
            except Exception as e:
                try:
                    with open("debug_launch_log.txt", "a", encoding="utf-8") as f:
                        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Failed to terminate: {e}\n")
                except Exception:
                    pass
        else:
            try:
                with open("debug_launch_log.txt", "a", encoding="utf-8") as f:
                    f.write(
                        f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Bypassing trainer termination! Orphaning process gracefully.\n")
            except Exception:
                pass

        # Allow the API response to send to the browser before cutting the cord
        time.sleep(0.5)
        try:
            with open("debug_launch_log.txt", "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Exiting os._exit(0)\n")
        except Exception:
            pass
        os._exit(0)

    threading.Thread(target=kill_process, daemon=True).start()
    return {"status": "success", "message": "System shutting down."}


def process_dental_positions(preds):
    if len(preds) < 2:
        return preds
        
    try:
        centers = []
        heights = []
        areas = []
        for p in preds:
            box = p["box"]
            cx = (box[0] + box[2]) / 2.0
            cy = (box[1] + box[3]) / 2.0
            h = box[3] - box[1]
            a = (box[2] - box[0]) * h
            centers.append([cx, cy])
            heights.append(h)
            areas.append(a)
            
        centers = np.array(centers)
        
        # Instead of PCA (which fails diagonally on asymmetric missing teeth), 
        # we determine orientation from the aspect ratio of the teeth.
        # Teeth are typically taller than they are wide.
        avg_w = np.mean([p["box"][2] - p["box"][0] for p in preds])
        avg_h = np.mean([p["box"][3] - p["box"][1] for p in preds])
        
        if avg_w > avg_h * 1.1:
            # Rotated 90 degrees
            primary_axis = np.array([0.0, 1.0])
            secondary_axis = np.array([-1.0, 0.0])
        else:
            # Upright
            primary_axis = np.array([1.0, 0.0])
            secondary_axis = np.array([0.0, 1.0])
            
        mean = np.mean(centers, axis=0)
        centered = centers - mean
            
        avg_height = np.mean(heights)
        x_proj = centered.dot(primary_axis)
        y_proj = centered.dot(secondary_axis)
        
        centrals = [i for i, p in enumerate(preds) if "Central Incisor" in p["label"]]
        two_jaws = False
        split_y = 0
        
        if len(centrals) >= 3:
            two_jaws = True
            sorted_c = sorted([y_proj[i] for i in centrals])
            max_gap = 0
            for i in range(len(sorted_c)-1):
                gap = sorted_c[i+1] - sorted_c[i]
                if gap > max_gap:
                    max_gap = gap
                    split_y = (sorted_c[i+1] + sorted_c[i]) / 2.0
        elif len(centrals) == 2:
            y_diff = abs(y_proj[centrals[0]] - y_proj[centrals[1]])
            if y_diff > avg_height * 0.5:
                two_jaws = True
                split_y = (y_proj[centrals[0]] + y_proj[centrals[1]]) / 2.0
        else:
            median_x = np.median(x_proj)
            center_teeth = [i for i in range(len(preds)) if abs(x_proj[i] - median_x) < avg_height * 1.5]
            if len(center_teeth) >= 2:
                y_center = [y_proj[i] for i in center_teeth]
                if (np.max(y_center) - np.min(y_center)) > avg_height * 0.75:
                    two_jaws = True
                    split_y = (np.max(y_center) + np.min(y_center)) / 2.0
                    
        upper_indices = []
        lower_indices = []
        
        if two_jaws:
            group0 = np.where(y_proj > split_y)[0]
            group1 = np.where(y_proj <= split_y)[0]
            
            if len(group0) > 0 and len(group1) > 0:
                cy0 = np.mean([centers[i][1] for i in group0])
                cy1 = np.mean([centers[i][1] for i in group1])
                
                # Image coordinates: smaller Y is higher on screen
                if cy0 < cy1: 
                    upper_indices = group0.tolist()
                    lower_indices = group1.tolist()
                else:
                    upper_indices = group1.tolist()
                    lower_indices = group0.tolist()
            else:
                upper_indices = list(range(len(preds)))
        else:
            is_lower = False
            if centrals:
                ratios = [ (preds[i]["box"][2]-preds[i]["box"][0]) / float(preds[i]["box"][3]-preds[i]["box"][1]) for i in centrals ]
                if np.mean(ratios) < 0.78:
                    is_lower = True
                    
            if is_lower:
                lower_indices = list(range(len(preds)))
            else:
                upper_indices = list(range(len(preds)))
            
        x_proj = centered.dot(primary_axis)
        if primary_axis[0] < 0:
            x_proj = -x_proj
            
        def assign_left_right(indices, prefix):
            if not indices: return
            
            sorted_idx = sorted(indices, key=lambda i: x_proj[i])
            centrals = [i for i in sorted_idx if "Central Incisor" in preds[i]["label"]]
            
            midline_x = None
            if len(centrals) >= 2:
                midline_x = (x_proj[centrals[0]] + x_proj[centrals[-1]]) / 2.0
            elif len(centrals) == 1:
                c_idx = sorted_idx.index(centrals[0])
                if c_idx > 0 and "Lateral" in preds[sorted_idx[c_idx-1]]["label"]:
                    midline_x = x_proj[centrals[0]] + 1.0
                elif c_idx < len(sorted_idx)-1 and "Lateral" in preds[sorted_idx[c_idx+1]]["label"]:
                    midline_x = x_proj[centrals[0]] - 1.0
                else:
                    midline_x = x_proj[centrals[0]]
            else:
                midline_x = np.mean([x_proj[i] for i in sorted_idx])
                
            for i in sorted_idx:
                label = preds[i]["label"]
                side = "R" if x_proj[i] < midline_x else "L"
                preds[i]["label"] = f"{prefix} {side} {label}"
                
        assign_left_right(upper_indices, "Maxillary")
        assign_left_right(lower_indices, "Mandibular")
        
    except Exception as e:
        print(f"Error in geometric processing: {e}")
        
    return preds

@app.post("/run_inference")
async def run_inference(
        image: UploadFile = File(...),
        conf_threshold: float = Form(0.25),
        active_models: str = Form(""),
        mode: str = Form(""),
        pipeline_mode: str = Form("sequential"),
        flow_graph: str = Form("{}"),
        autopilot_model: str = Form(""),
        all_presets: str = Form("{}"),
        use_dental_position: str = Form("false")
):
    start_time = time.time()
    img_bytes = await image.read()
    nparr = np.frombuffer(img_bytes, np.uint8)
    original_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if original_img is None:
        return JSONResponse(status_code=400, content={"error": "Invalid or corrupted image file provided."})
    isolated_base_img = cv2.resize(original_img, (640, 640))

    margin = 250
    canvas_w = 640 + (margin * 2)
    canvas_h = 640
    UI_BG_COLOR = (42, 23, 15)
    master_canvas = np.full((canvas_h, canvas_w, 3), UI_BG_COLOR, dtype=np.uint8)
    master_canvas[0:640, margin:margin + 640] = isolated_base_img
    glow_layer = np.zeros_like(master_canvas)
    all_predictions = []
    dental_predictions = []

    predicted_preset = None

    # Execute inference pipeline
    if pipeline_mode == "custom":
        if autopilot_model and autopilot_model != "":
            model_path = os.path.join(AUTOPILOT_OUT_DIR, autopilot_model)
            if os.path.exists(model_path):
                if autopilot_model not in models:
                    models[autopilot_model] = YOLO(model_path, task='classify')

                router = models[autopilot_model]

                router_results = router.predict(source=isolated_base_img, imgsz=224, verbose=False)
                top_id = int(router_results[0].probs.top1)
                predicted_preset = router_results[0].names[top_id]

                try:
                    presets_dict = json.loads(all_presets)
                    if predicted_preset in presets_dict:
                        graph_data = presets_dict[predicted_preset]
                    else:
                        graph_data = json.loads(flow_graph)
                except Exception:
                    graph_data = json.loads(flow_graph)
            else:
                graph_data = json.loads(flow_graph) if flow_graph != "{}" else {}
        else:
            graph_data = json.loads(flow_graph) if flow_graph != "{}" else {}

        try:
            nodes_dict = {n['id']: n for n in graph_data.get('nodes', [])}
            edges = graph_data.get('edges', [])
            queue = []
            executed_nodes = set()
            model_cache = {}

            for n_id, n in nodes_dict.items():
                if n['type'] == 'start':
                    executed_nodes.add(n_id)
                    for edge in edges:
                        if edge['from'] == n_id:
                            queue.append(edge['to'])
                    break

            while queue:
                curr_id = queue.pop(0)
                if curr_id in executed_nodes or curr_id not in nodes_dict:
                    continue
                node = nodes_dict[curr_id]
                if node['type'] == 'end':
                    executed_nodes.add(curr_id)
                    continue
                if node['type'] == 'model':
                    model_name = node.get('modelName')
                    if not model_name or model_name not in models:
                        executed_nodes.add(curr_id)
                        continue
                    if model_name not in model_cache:
                        model_obj = models[model_name]
                        fresh_copy = isolated_base_img.copy()
                        results = model_obj.predict(source=fresh_copy, conf=conf_threshold, imgsz=640, verbose=False)
                        preds = []
                        detected_classes = set()
                        for box in results[0].boxes:
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            conf = float(box.conf[0])
                            cls_id = int(box.cls[0])
                            class_name = model_obj.names[cls_id]
                            preds.append({
                                "box": [x1, y1, x2, y2],
                                "conf": conf,
                                "label": class_name,
                                "color": model_colors[model_name]
                            })
                            
                        if model_name == "DENTALPOSITION_R_98.onnx":
                            preds = process_dental_positions(preds)
                            
                        for p in preds:
                            detected_classes.add(p["label"])
                            
                        model_cache[model_name] = {"predictions": preds, "detected_classes": detected_classes}
                    executed_nodes.add(curr_id)
                    detected = model_cache[model_name]["detected_classes"]
                    for edge in edges:
                        if edge['from'] == curr_id:
                            if edge['fromPort'] in detected:
                                queue.append(edge['to'])

            end_node_ids = [n_id for n_id, n in nodes_dict.items() if n['type'] == 'end']
            for n_id in executed_nodes:
                if n_id in nodes_dict and nodes_dict[n_id]['type'] == 'model':
                    node = nodes_dict[n_id]
                    if node.get('filterResults') is False:
                        model_name = node.get('modelName')
                        if model_name and model_name in model_cache:
                            for pred in model_cache[model_name]["predictions"]:
                                if model_name == "DENTALPOSITION_R_98.onnx":
                                    if pred not in dental_predictions:
                                        dental_predictions.append(pred)
                                else:
                                    if pred not in all_predictions:
                                        all_predictions.append(pred)

            for edge in edges:
                if edge['to'] in end_node_ids:
                    source_id = edge['from']
                    source_port = edge['fromPort']
                    if source_id in executed_nodes and source_id in nodes_dict:
                        node = nodes_dict[source_id]
                        model_name = node.get('modelName')
                        if node.get('filterResults', True) is True and model_name and model_name in model_cache:
                            for pred in model_cache[model_name]["predictions"]:
                                if pred["label"] == source_port:
                                    if model_name == "DENTALPOSITION_R_98.onnx":
                                        if pred not in dental_predictions:
                                            dental_predictions.append(pred)
                                    else:
                                        if pred not in all_predictions:
                                            all_predictions.append(pred)
        except Exception as e:
            pass
    else:
        models_to_run = [m.strip() for m in active_models.split(",") if m.strip()]
        if use_dental_position == "true" and "DENTALPOSITION_R_98.onnx" in models and "DENTALPOSITION_R_98.onnx" not in models_to_run:
            models_to_run.append("DENTALPOSITION_R_98.onnx")
            
        for model_name in models_to_run:
            if model_name in models:
                model_obj = models[model_name]
                fresh_copy = isolated_base_img.copy()
                results = model_obj.predict(source=fresh_copy, conf=conf_threshold, imgsz=640, verbose=False)
                preds = []
                for box in results[0].boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0])
                    cls_id = int(box.cls[0])
                    class_name = model_obj.names[cls_id]
                    preds.append({
                        "box": [x1, y1, x2, y2],
                        "conf": conf,
                        "label": class_name,
                        "color": model_colors[model_name]
                    })
                    
                if model_name == "DENTALPOSITION_R_98.onnx":
                    preds = process_dental_positions(preds)
                    dental_predictions.extend(preds)
                else:
                    all_predictions.extend(preds)

    if dental_predictions:
        for pred in all_predictions:
            best_tooth = None
            best_tooth_box = None
            
            # 1. Primary matching: Check all overlaps
            overlaps = []
            disease_w = pred["box"][2] - pred["box"][0]
            disease_h = pred["box"][3] - pred["box"][1]
            disease_area = max(1, disease_w * disease_h)
            
            for d_pred in dental_predictions:
                xA = max(pred["box"][0], d_pred["box"][0])
                yA = max(pred["box"][1], d_pred["box"][1])
                xB = min(pred["box"][2], d_pred["box"][2])
                yB = min(pred["box"][3], d_pred["box"][3])
                interArea = max(0, xB - xA) * max(0, yB - yA)
                
                if interArea > 0:
                    overlaps.append((interArea, d_pred["label"], d_pred["box"]))
            
            if overlaps:
                overlaps.sort(key=lambda x: x[0], reverse=True)
                
                # Check for cross-midline spanning (e.g. overlaps both L and R Central Incisors)
                if len(overlaps) >= 2:
                    area1, label1, box1 = overlaps[0]
                    area2, label2, box2 = overlaps[1]
                    
                    # If both teeth have significant overlap (>15% of disease area)
                    if area1 > 0.15 * disease_area and area2 > 0.15 * disease_area:
                        parts1 = label1.split(" ")
                        parts2 = label2.split(" ")
                        
                        if len(parts1) >= 3 and len(parts2) >= 3:
                            jaw1, side1, type1 = parts1[0], parts1[1], " ".join(parts1[2:])
                            jaw2, side2, type2 = parts2[0], parts2[1], " ".join(parts2[2:])
                            
                            # If they are the same jaw and same tooth type, but different sides (L vs R)
                            if jaw1 == jaw2 and type1 == type2 and side1 != side2:
                                best_tooth = f"{jaw1} {type1}"
                                best_tooth_box = [min(box1[0], box2[0]), min(box1[1], box2[1]), max(box1[2], box2[2]), max(box1[3], box2[3])]
                
                # Fallback to the largest overlap if not spanning
                if not best_tooth:
                    best_tooth = overlaps[0][1]
                    best_tooth_box = overlaps[0][2]
                    
            # 2. Fallback matching: If no overlap, find the tooth with the closest center
            if not best_tooth:
                cx = (pred["box"][0] + pred["box"][2]) / 2.0
                cy = (pred["box"][1] + pred["box"][3]) / 2.0
                min_dist = float('inf')
                for d_pred in dental_predictions:
                    dcx = (d_pred["box"][0] + d_pred["box"][2]) / 2.0
                    dcy = (d_pred["box"][1] + d_pred["box"][3]) / 2.0
                    dist = ((cx - dcx)**2 + (cy - dcy)**2) ** 0.5
                    
                    # Max allowed distance is 3.0x the size of the tooth box to catch gumline or adjacent missing teeth
                    tooth_w = d_pred["box"][2] - d_pred["box"][0]
                    tooth_h = d_pred["box"][3] - d_pred["box"][1]
                    max_allowed = max(tooth_w, tooth_h) * 3.0
                    
                    if dist < min_dist and dist < max_allowed:
                        min_dist = dist
                        best_tooth = d_pred["label"]
                        best_tooth_box = d_pred["box"]
            
            if best_tooth:
                pred["tooth_position"] = best_tooth
                pred["tooth_box"] = best_tooth_box

    filtered_predictions = []
    all_predictions = sorted(all_predictions, key=lambda x: x['conf'], reverse=True)
    for pred in all_predictions:
        keep = True
        for kept_pred in filtered_predictions:
            if get_iou(pred["box"], kept_pred["box"]) > 0.4 and pred["label"] == kept_pred["label"]:
                keep = False
                break
        if keep:
            filtered_predictions.append(pred)

    summary_counts = dict(Counter([pred["label"] for pred in filtered_predictions]))

    summary_grouped = {}
    for pred in filtered_predictions:
        tooth = pred.get("tooth_position", "General")
        label = pred["label"]
        if tooth not in summary_grouped:
            summary_grouped[tooth] = {}
        if label not in summary_grouped[tooth]:
            summary_grouped[tooth][label] = 0
        summary_grouped[tooth][label] += 1

    detailed_findings = []
    for pred in filtered_predictions:
        tb = pred.get("tooth_box", None)
        detailed_findings.append({
            "label": pred["label"],
            "confidence": round(float(pred["conf"]), 2),
            "tooth_position": pred.get("tooth_position", "General"),
            "disease_box": [float(c) for c in pred["box"]],
            "tooth_box": [float(c) for c in tb] if tb else None
        })

    left_preds = []
    right_preds = []
    for pred in filtered_predictions:
        x1, y1, x2, y2 = pred["box"]
        x1 += margin
        x2 += margin
        pred["box"] = [x1, y1, x2, y2]
        draw_modern_box_only(master_canvas, glow_layer, x1, y1, x2, y2, pred["color"])
        bx = (x1 + x2) // 2
        by = (y1 + y2) // 2
        pred["center"] = (bx, by)
        if bx < (margin + 320):
            left_preds.append(pred)
        else:
            right_preds.append(pred)

    left_preds.sort(key=lambda x: x["center"][1])
    right_preds.sort(key=lambda x: x["center"][1])

    try:
        ui_font = ImageFont.truetype("segoeui.ttf", 14)
    except IOError:
        try:
            ui_font = ImageFont.truetype("arial.ttf", 14)
        except IOError:
            ui_font = ImageFont.load_default()

    text_render_queue = []

    def draw_hud_callouts(preds, is_left):
        if not preds: return
        total = len(preds)
        step = min(50, 600 // total)
        avg_y = sum(p["center"][1] for p in preds) / total
        start_y = max(30, avg_y - (step * total) / 2)
        if start_y + step * total > 610:
            start_y = max(30, 610 - step * total)

        for i, pred in enumerate(preds):
            target_y = int(start_y + i * step)
            x1, y1, x2, y2 = pred["box"]
            bx, by = pred["center"]
            color = pred["color"]
            rgb_color = (color[2], color[1], color[0])
            label = f"{pred['label'].upper()} [{pred['conf']:.2f}]"
            if hasattr(ui_font, 'getbbox'):
                bbox = ui_font.getbbox(label)
                w = bbox[2] - bbox[0]
                h = bbox[3] - bbox[1]
            else:
                try:
                    w, h = ui_font.getsize(label)
                except:
                    w, h = (120, 14)

            if is_left:
                start_x = x1
                elbow1_x = x1 - 15
                elbow2_x = margin - 25
                end_x = margin - 45
                cv2.line(glow_layer, (start_x, by), (elbow1_x, by), color, 2, cv2.LINE_AA)
                cv2.line(glow_layer, (elbow1_x, by), (elbow2_x, target_y), color, 2, cv2.LINE_AA)
                cv2.line(glow_layer, (elbow2_x, target_y), (end_x, target_y), color, 2, cv2.LINE_AA)
                cv2.line(master_canvas, (start_x, by), (elbow1_x, by), color, 1, cv2.LINE_AA)
                cv2.line(master_canvas, (elbow1_x, by), (elbow2_x, target_y), color, 1, cv2.LINE_AA)
                cv2.line(master_canvas, (elbow2_x, target_y), (end_x, target_y), color, 1, cv2.LINE_AA)
                box_x1 = end_x - w - 24
                box_y1 = target_y - h - 10
                box_x2 = end_x
                box_y2 = target_y + 10
                cv2.rectangle(glow_layer, (box_x1, box_y1), (box_x2, box_y2), color, 1)
                cv2.rectangle(master_canvas, (box_x1, box_y1), (box_x2, box_y2), UI_BG_COLOR, -1)
                cv2.rectangle(master_canvas, (box_x1, box_y1), (box_x2, box_y2), color, 1)
                cv2.line(master_canvas, (box_x2, box_y1), (box_x2, box_y2), color, 2)
                text_render_queue.append(
                    {"label": label, "x": box_x1 + 12, "y": box_y1 + ((box_y2 - box_y1 - h) // 2) - 2,
                     "color": rgb_color})
            else:
                start_x = x2
                elbow1_x = x2 + 15
                elbow2_x = margin + 640 + 25
                end_x = margin + 640 + 45
                cv2.line(glow_layer, (start_x, by), (elbow1_x, by), color, 2, cv2.LINE_AA)
                cv2.line(glow_layer, (elbow1_x, by), (elbow2_x, target_y), color, 2, cv2.LINE_AA)
                cv2.line(glow_layer, (elbow2_x, target_y), (end_x, target_y), color, 2, cv2.LINE_AA)
                cv2.line(master_canvas, (start_x, by), (elbow1_x, by), color, 1, cv2.LINE_AA)
                cv2.line(master_canvas, (elbow1_x, by), (elbow2_x, target_y), color, 1, cv2.LINE_AA)
                cv2.line(master_canvas, (elbow2_x, target_y), (end_x, target_y), color, 1, cv2.LINE_AA)
                box_x1 = end_x
                box_y1 = target_y - h - 10
                box_x2 = end_x + w + 24
                box_y2 = target_y + 10
                cv2.rectangle(glow_layer, (box_x1, box_y1), (box_x2, box_y2), color, 1)
                cv2.rectangle(master_canvas, (box_x1, box_y1), (box_x2, box_y2), UI_BG_COLOR, -1)
                cv2.rectangle(master_canvas, (box_x1, box_y1), (box_x2, box_y2), color, 1)
                cv2.line(master_canvas, (box_x1, box_y1), (box_x1, box_y2), color, 2)
                text_render_queue.append(
                    {"label": label, "x": box_x1 + 12, "y": box_y1 + ((box_y2 - box_y1 - h) // 2) - 2,
                     "color": rgb_color})

    draw_hud_callouts(left_preds, is_left=True)
    draw_hud_callouts(right_preds, is_left=False)

    master_pil = Image.fromarray(cv2.cvtColor(master_canvas, cv2.COLOR_BGR2RGB))
    glow_pil = Image.fromarray(cv2.cvtColor(glow_layer, cv2.COLOR_BGR2RGB))
    draw_master = ImageDraw.Draw(master_pil)
    draw_glow = ImageDraw.Draw(glow_pil)
    soft_white = (240, 245, 250)

    for job in text_render_queue:
        draw_glow.text((job["x"], job["y"]), job["label"], font=ui_font, fill=job["color"])
        draw_master.text((job["x"], job["y"]), job["label"], font=ui_font, fill=soft_white)

    master_canvas = cv2.cvtColor(np.array(master_pil), cv2.COLOR_RGB2BGR)
    glow_layer = cv2.cvtColor(np.array(glow_pil), cv2.COLOR_RGB2BGR)

    blurred_glow = cv2.GaussianBlur(glow_layer, (9, 9), 0)
    final_output = cv2.addWeighted(master_canvas, 1.0, blurred_glow, 0.6, 0)

    total_time = round(time.time() - start_time, 3)
    _, buffer = cv2.imencode('.jpg', final_output)
    base64_img = base64.b64encode(buffer).decode('utf-8')

    return JSONResponse({
        "status": "success",
        "image_base64": f"data:image/jpeg;base64,{base64_img}",
        "time_taken": total_time,
        "detections": len(filtered_predictions),
        "summary": summary_counts,
        "summary_grouped": summary_grouped,
        "detailed_findings": detailed_findings,
        "routed_flow": predicted_preset
    })


mobile_upload_history: List[Dict] = []
mobile_upload_id = None

import time
from pydantic import BaseModel

class MobilePing(BaseModel):
    device_id: str
    device_name: str

active_mobile_devices = {}

@app.post("/mobile_ping")
def mobile_ping(data: MobilePing):
    active_mobile_devices[data.device_id] = {
        "name": data.device_name,
        "last_ping": time.time()
    }
    return {"status": "ok"}

@app.get("/connected_devices")
def get_connected_devices():
    current_time = time.time()
    active = [
        {"id": d_id, "name": info["name"]}
        for d_id, info in active_mobile_devices.items()
        if current_time - info["last_ping"] < 10
    ]
    return JSONResponse({"devices": active})


import uuid

def get_lan_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
        s.close()
    except Exception:
        IP = '127.0.0.1'
    return IP

@app.get("/get_qr_codes")
def get_qr_codes(ssid: str = "", password: str = ""):
    ip = get_lan_ip()
    url = f"http://{ip}:8000/mobile_camera?token={SESSION_TOKEN}"
    
    qr_url = qrcode.QRCode(version=1, box_size=10, border=4)
    qr_url.add_data(url)
    qr_url.make(fit=True)
    img_url = qr_url.make_image(fill_color="black", back_color="white")
    buf_url = io.BytesIO()
    img_url.save(buf_url, format="PNG")
    b64_url = base64.b64encode(buf_url.getvalue()).decode("utf-8")
    
    b64_wifi = ""
    if ssid:
        wifi_str = f"WIFI:S:{ssid};T:WPA;P:{password};;"
        qr_wifi = qrcode.QRCode(version=1, box_size=10, border=4)
        qr_wifi.add_data(wifi_str)
        qr_wifi.make(fit=True)
        img_wifi = qr_wifi.make_image(fill_color="black", back_color="white")
        buf_wifi = io.BytesIO()
        img_wifi.save(buf_wifi, format="PNG")
        b64_wifi = base64.b64encode(buf_wifi.getvalue()).decode("utf-8")
        
    return JSONResponse({
        "url_qr": f"data:image/png;base64,{b64_url}",
        "wifi_qr": f"data:image/png;base64,{b64_wifi}" if b64_wifi else "",
        "url": url
    })

@app.get("/mobile_camera")
def mobile_camera():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
        <title>SmiloAI Mobile Capture</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #000; color: #fff; text-align: center; padding: 20px; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; }
            h2 { font-weight: 600; margin-bottom: 30px; }
            .btn { background: #007AFF; color: white; border: none; padding: 15px 30px; border-radius: 12px; font-size: 18px; font-weight: bold; cursor: pointer; width: 100%; box-shadow: 0 4px 12px rgba(0,122,255,0.4); }
            .btn-container { position: relative; width: 80%; max-width: 300px; margin-bottom: 20px; overflow: hidden; border-radius: 12px; }
            input[type="file"] { position: absolute; left: 0; top: 0; width: 100%; height: 100%; opacity: 0; cursor: pointer; z-index: 10; }
            #status { margin-top: 20px; font-size: 16px; color: #aaa; }
        </style>
    </head>
    <body>
        <h2>SmiloAI Capture</h2>
        <div class="btn-container">
            <button class="btn">📸 Open Camera</button>
            <input type="file" id="cameraInput" accept="image/*" multiple>
        </div>
        <div id="status">Ready to capture.</div>
        
        <script>
            function getDeviceName() {
                var ua = navigator.userAgent;
                if (/iPad/.test(ua)) return "iPad";
                if (/iPhone/.test(ua)) return "iPhone";
                if (/Android/.test(ua)) return "Android";
                if (/Mac OS X/.test(ua)) return "Mac";
                if (/Windows/.test(ua)) return "Windows";
                return "Smartphone";
            }
            
            var deviceId = localStorage.getItem('smiloai_device_id');
            if (!deviceId) {
                deviceId = 'dev_' + Math.random().toString(36).substr(2, 9);
                localStorage.setItem('smiloai_device_id', deviceId);
            }
            var deviceName = getDeviceName();

            function pingServer() {
                fetch('/mobile_ping', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ device_id: deviceId, device_name: deviceName })
                }).catch(e => console.log('Ping failed'));
            }
            
            pingServer();
            setInterval(pingServer, 3000);

            document.getElementById('cameraInput').addEventListener('change', function(e) {
                const files = e.target.files;
            if (!files || files.length === 0) return;

            document.getElementById('status').innerText = "Uploading " + files.length + " photo(s)...";
            document.getElementById('status').style.color = "#FF9500";
            document.querySelector('.btn').style.opacity = '0.5';

            const formData = new FormData();
            for (let i = 0; i < files.length; i++) {
                formData.append('files', files[i]);
            }
            
            const params = new URLSearchParams(window.location.search);
            const token = params.get('token');

            fetch('/upload_from_mobile?token=' + token, {
                method: 'POST',
                body: formData
            })
            .then(res => res.json())
            .then(data => {
                document.querySelector('.btn').style.opacity = '1';
                if (data.status === 'success') {
                    document.getElementById('status').innerText = "✅ Sent " + files.length + " Photo(s) to Desktop!";
                    document.getElementById('status').style.color = "#34C759";
                } else {
                    document.getElementById('status').innerText = "❌ Upload Failed";
                    document.getElementById('status').style.color = "#FF3B30";
                }
            })
            .catch(err => {
                document.querySelector('.btn').style.opacity = '1';
                document.getElementById('status').innerText = "❌ Network Error.";
                document.getElementById('status').style.color = "#FF3B30";
            });
        });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

@app.post("/upload_from_mobile")
async def upload_from_mobile(files: List[UploadFile] = File(...)):
    global mobile_upload_history
    for file in files:
        print(f"[Mobile Upload] Incoming file: {file.filename} / Content-Type: {file.content_type}")
        contents = await file.read()
        new_id = str(uuid.uuid4())
        mobile_upload_history.append({"id": new_id, "blob": contents})
        # Keep only the last 50 images in memory to prevent Denial of Service via memory exhaustion
        if len(mobile_upload_history) > 50:
            mobile_upload_history.pop(0)
        print(f"[Mobile Upload] Successfully cached {len(contents)} bytes in memory with ID: {new_id}.")
    return {"status": "success"}

@app.get("/check_mobile_upload")
def check_mobile_upload(last_id: str = "", init: str = ""):
    global mobile_upload_history
    if init == "true":
        latest_id = mobile_upload_history[-1]["id"] if mobile_upload_history else ""
        return JSONResponse({"status": "success", "upload_id": latest_id})
    
    new_images = []
    found_last = False
    
    if not last_id:
        # If no last_id is provided, just return the entire history? 
        # Wait, if last_id is empty, it means we want everything since session started.
        found_last = True
        
    for item in mobile_upload_history:
        if found_last:
            b64 = base64.b64encode(item["blob"]).decode("utf-8")
            new_images.append({
                "id": item["id"],
                "image_base64": f"data:image/jpeg;base64,{b64}"
            })
        if item["id"] == last_id:
            found_last = True
            
    if new_images:
        return JSONResponse({
            "status": "success", 
            "images": new_images,
            "upload_id": new_images[-1]["id"]
        })
        
    return JSONResponse({"status": "waiting"})


if __name__ == "__main__":
    print("Starting SmiloAI...")
    uvicorn.run(app, host="0.0.0.0", port=8000)