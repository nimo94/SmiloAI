import sys
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

# PyInstaller native splash screen module
try:
    import pyi_splash
except ImportError:
    pyi_splash = None

try:
    import requests
    import dropbox
    from groq import Groq
except ImportError:
    print("WARNING: Missing libraries. Run 'pip install requests dropbox groq' to enable Cloud & AI features.")

os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

# Cloud and API configuration (Load from environment or fallback to safe placeholders)
APP_KEY = os.getenv("DROPBOX_APP_KEY", "YOUR_DROPBOX_APP_KEY_HERE")
APP_SECRET = os.getenv("DROPBOX_APP_SECRET", "YOUR_DROPBOX_APP_SECRET_HERE")
REFRESH_TOKEN = os.getenv("DROPBOX_REFRESH_TOKEN", "YOUR_DROPBOX_REFRESH_TOKEN_HERE")
DROPBOX_FOLDER_PATH = os.getenv("DROPBOX_FOLDER_PATH", "/home/Aswin Selvam/Apps/SmiloAI/MODELS")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "YOUR_GROQ_API_KEY_HERE")


def get_access_token_from_refresh_token(app_key, app_secret, refresh_token):
    try:
        auth_url = 'https://api.dropbox.com/oauth2/token'
        auth_data = {
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
            'client_id': app_key,
            'client_secret': app_secret,
        }
        response = requests.post(auth_url, data=auth_data, timeout=10)
        response.raise_for_status()
        return response.json().get('access_token')
    except Exception as e:
        print(f"Dropbox authentication failed: {e}")
        return None


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
@asynccontextmanager
async def lifespan(app: FastAPI):
    def open_url():
        time.sleep(1.0)
        if pyi_splash and pyi_splash.is_alive():
            pyi_splash.close()

        print("Launching SmiloGui in the default browser...")
        webbrowser.open("http://127.0.0.1:8000")

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


app = FastAPI(title="SmiloAi Engine", version="5.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:8000",
        "http://127.0.0.1:3000",
        "http://localhost:3000",
        "http://127.0.0.1:5000",
        "http://localhost:5000",
        "null"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        if not GROQ_API_KEY or "YOUR_GROQ_API_KEY" in GROQ_API_KEY:
            yield "data: [ERROR] Valid GROQ_API_KEY required for AI Clinical Assistant.\n\n"
            return

        try:
            client = Groq(api_key=GROQ_API_KEY)
            scan_context = "an intraoral RGB photograph of a patient's teeth and gums" if mode == "rgb" else "a patient's dental X-Ray"

            prompt = (
                f"You are SmiloAi, a highly advanced clinical dental assistant. The vision engine just scanned {scan_context} "
                f"and detected the following issues: {detections}. "
                f"Write a short, highly professional, but reassuring paragraph (3-4 sentences max) explaining what this means "
                f"and what the standard clinical procedure (like drilling and filling for caries, scaling for calculus, etc.) will be in the clinic. "
                f"Do not use markdown formatting (* or #), just plain readable text."
            )

            stream = client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[{"role": "user", "content": prompt}],
                stream=True,
            )

            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    text = chunk.choices[0].delta.content.replace('\n', '<br>')
                    yield f"data: {text}\n\n"

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
        if DROPBOX_FOLDER_PATH != "":
            access_token = get_access_token_from_refresh_token(APP_KEY, APP_SECRET, REFRESH_TOKEN)
            if access_token:
                dbx = dropbox.Dropbox(access_token)
                search_path = DROPBOX_FOLDER_PATH.rstrip('/')
                result = dbx.files_list_folder(search_path)
                for entry in result.entries:
                    if isinstance(entry, dropbox.files.FileMetadata):
                        if entry.name.endswith(".pt") or entry.name.endswith(".onnx"):
                            available_models.append(entry.name)
    except Exception:
        pass

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
            access_token = get_access_token_from_refresh_token(APP_KEY, APP_SECRET, REFRESH_TOKEN)
            if not access_token:
                yield f"data: ERROR:Authentication failed.\n\n"
                return
            dbx = dropbox.Dropbox(access_token)
            dbx_path = f"{DROPBOX_FOLDER_PATH.rstrip('/')}/{clean_name}"
            link_result = dbx.files_get_temporary_link(dbx_path)
            total_size = link_result.metadata.size
            with requests.get(link_result.link, stream=True, timeout=15) as r:
                r.raise_for_status()
                downloaded = 0
                with open(file_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024 * 256):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                progress = int((downloaded / total_size) * 100)
                                yield f"data: {progress}\n\n"
            yield f"data: 100\n\n"
            models[model_name] = YOLO(file_path)
            model_colors[model_name] = random.choice(MODERN_COLORS)
            yield f"data: DONE\n\n"
        except Exception as e:
            yield f"data: ERROR:{str(e)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/save_training_data")
async def save_training_data(image: UploadFile = File(...), label: str = Form(...)):
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
async def load_model(file: UploadFile = File(...)):
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
async def remove_model(model_name: str = Form(...)):
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


@app.post("/run_inference")
async def run_inference(
        image: UploadFile = File(...),
        conf_threshold: float = Form(0.25),
        active_models: str = Form(""),
        mode: str = Form(""),
        pipeline_mode: str = Form("sequential"),
        flow_graph: str = Form("{}"),
        autopilot_model: str = Form(""),
        all_presets: str = Form("{}")
):
    start_time = time.time()
    img_bytes = await image.read()
    nparr = np.frombuffer(img_bytes, np.uint8)
    original_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    isolated_base_img = cv2.resize(original_img, (640, 640))

    margin = 250
    canvas_w = 640 + (margin * 2)
    canvas_h = 640
    UI_BG_COLOR = (42, 23, 15)
    master_canvas = np.full((canvas_h, canvas_w, 3), UI_BG_COLOR, dtype=np.uint8)
    master_canvas[0:640, margin:margin + 640] = isolated_base_img
    glow_layer = np.zeros_like(master_canvas)
    all_predictions = []

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
                            detected_classes.add(class_name)
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
                                if pred["label"] == source_port and pred not in all_predictions:
                                    all_predictions.append(pred)
        except Exception as e:
            pass
    else:
        models_to_run = [m.strip() for m in active_models.split(",") if m.strip()]
        for model_name in models_to_run:
            if model_name in models:
                model_obj = models[model_name]
                fresh_copy = isolated_base_img.copy()
                results = model_obj.predict(source=fresh_copy, conf=conf_threshold, imgsz=640, verbose=False)
                for box in results[0].boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0])
                    cls_id = int(box.cls[0])
                    class_name = model_obj.names[cls_id]
                    all_predictions.append({
                        "box": [x1, y1, x2, y2],
                        "conf": conf,
                        "label": class_name,
                        "color": model_colors[model_name]
                    })

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
        "routed_flow": predicted_preset
    })


if __name__ == "__main__":
    print("Starting SmiloAi Engine...")
    uvicorn.run(app, host="127.0.0.1", port=8000)