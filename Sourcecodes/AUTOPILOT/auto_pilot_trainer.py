import customtkinter as ctk
import tkinter as tk
import tkinter.messagebox as messagebox
import os
import sys
import shutil
import random
import threading
import queue
import time
import traceback
from PIL import Image, ImageTk
import pandas as pd
from ultralytics import YOLO
import ultralytics

ultralytics.utils.ONLINE = False

# ✨ Force Matplotlib into "Headless/Background" mode globally to prevent thread crashes!
import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# ✨ IMPORT PYI_SPLASH TO CONTROL THE BOOT SCREEN
try:
    import pyi_splash
except ImportError:
    pyi_splash = None

# ==========================================================
# 🛡️ THE .EXE "NO CONSOLE" CRASH PROTECTOR
# ==========================================================
os.environ["PYTHONIOENCODING"] = "utf-8"

if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")


def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


# ==========================================================
# 🎨 UI CONFIGURATION & FOLDER MANAGEMENT
# ==========================================================
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

# ✨ THE FIX: Removed the buggy "AUTOPILOT" folder injection!
# It now points strictly back to the exact root folders where your data actually lives.
BASE_DATA_DIR = os.path.join(APP_DIR, "Training_Data")
BALANCED_DATA_DIR = os.path.join(APP_DIR, "Training_Data_Balanced")
AUTOPILOT_OUT_DIR = os.path.join(APP_DIR, "AUTOPILOT_MODELS")

os.makedirs(BASE_DATA_DIR, exist_ok=True)
os.makedirs(AUTOPILOT_OUT_DIR, exist_ok=True)


class AutoPilotTrainer(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("SmiloAi - Auto-Pilot Training Engine")
        self.geometry("1000x720")
        self.minsize(800, 550)
        self.resizable(True, True)

        logo_path = get_resource_path("logo.png")
        if os.path.exists(logo_path):
            try:
                pil_icon = Image.open(logo_path)
                self.icon_img = ImageTk.PhotoImage(pil_icon)
                self.wm_iconphoto(True, self.icon_img)

                if os.name == 'nt':
                    import tempfile
                    ico_path = os.path.join(tempfile.gettempdir(), "smilo_icon.ico")
                    pil_icon.save(ico_path, format="ICO", sizes=[(64, 64)])
                    self.iconbitmap(ico_path)
            except Exception as e:
                print(f"Icon warning: {e}")

        self.metric_queue = queue.Queue()
        self.epochs_history = []
        self.acc_history = []
        self.loss_history = []
        self.stop_requested = False

        self.setup_ui()
        self.check_queue()

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(0, weight=1)

        self.left_frame = ctk.CTkFrame(self, corner_radius=15, fg_color="#1e293b")
        self.left_frame.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="nsew")
        self.left_frame.grid_columnconfigure(0, weight=1)

        self.header_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(15, 5))

        logo_path = get_resource_path("logo.png")
        try:
            pil_img = Image.open(logo_path)
            w, h = pil_img.size
            new_h = 100
            new_w = int((new_h / h) * w)
            logo_ctk = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(new_w, new_h))
            self.title_label = ctk.CTkLabel(self.header_frame, text="", image=logo_ctk)
        except Exception:
            self.title_label = ctk.CTkLabel(self.header_frame, text="🧠 Auto-Pilot",
                                            font=ctk.CTkFont(size=28, weight="bold"), text_color="#a855f7")
        self.title_label.pack()

        self.class_lbl = ctk.CTkLabel(self.left_frame, text="TARGET SPECIALISTS",
                                      font=ctk.CTkFont(size=11, weight="bold"), text_color="#94a3b8")
        self.class_lbl.grid(row=1, column=0, sticky="w", pady=(10, 0), padx=20)

        self.classes_inner_frame = ctk.CTkScrollableFrame(self.left_frame, fg_color="#0f172a", corner_radius=8,
                                                          height=120)
        self.classes_inner_frame.grid(row=2, column=0, sticky="nsew", pady=(5, 10), padx=15)

        self.class_vars = {}
        self.load_classes()

        self.term_header = ctk.CTkFrame(self.left_frame, fg_color="#334155", corner_radius=5, height=25)
        self.term_header.grid(row=3, column=0, sticky="ew", padx=15, pady=(5, 0))
        self.term_header.pack_propagate(False)
        ctk.CTkLabel(self.term_header, text=">_ ENGINE TERMINAL", font=ctk.CTkFont(size=10, weight="bold"),
                     text_color="#94a3b8").pack(side="left", padx=10)

        self.status_box = ctk.CTkTextbox(self.left_frame, fg_color="#0b1121", border_width=1, border_color="#334155",
                                         corner_radius=5, text_color="#10b981",
                                         font=ctk.CTkFont(family="Consolas", size=11))
        self.status_box.grid(row=4, column=0, sticky="nsew", padx=15, pady=(0, 10))
        self.status_box.insert("0.0", "System Ready.\nConfigure settings and initiate sequence...\n")
        self.status_box.configure(state="disabled")

        self.bottom_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.bottom_frame.grid(row=5, column=0, sticky="ew", pady=(0, 15))

        self.acc_title = ctk.CTkLabel(self.bottom_frame, text="CURRENT ACCURACY",
                                      font=ctk.CTkFont(size=11, weight="bold"), text_color="#64748b")
        self.acc_title.pack()

        self.acc_value = ctk.CTkLabel(self.bottom_frame, text="--%", font=ctk.CTkFont(size=48, weight="bold"),
                                      text_color="#38bdf8")
        self.acc_value.pack()

        self.progress_bar = ctk.CTkProgressBar(self.bottom_frame, progress_color="#a855f7", mode="determinate")
        self.progress_bar.pack(padx=15, pady=(5, 0), fill="x")
        self.progress_bar.set(0)

        self.time_label = ctk.CTkLabel(self.bottom_frame, text="EST. TIME REMAINING: --:--",
                                       font=ctk.CTkFont(size=10, weight="bold"), text_color="#64748b")
        self.time_label.pack(pady=(2, 10))

        self.btn_train = ctk.CTkButton(self.bottom_frame, text="INITIATE TRAINING", font=ctk.CTkFont(weight="bold"),
                                       fg_color="#8b5cf6", hover_color="#7c3aed", height=45,
                                       command=self.start_training_process)
        self.btn_train.pack(padx=15, pady=(0, 10), fill="x")

        self.btn_stop = ctk.CTkButton(self.bottom_frame, text="🛑 SAFE STOP", font=ctk.CTkFont(weight="bold"),
                                      fg_color="#475569", hover_color="#e11d48", height=45, state="disabled",
                                      command=self.request_safe_stop)
        self.btn_stop.pack(padx=15, fill="x")

        self.right_frame = ctk.CTkFrame(self, corner_radius=15, fg_color="#0f172a")
        self.right_frame.grid(row=0, column=1, padx=(10, 20), pady=20, sticky="nsew")

        self.params_frame = ctk.CTkFrame(self.right_frame, fg_color="#1e293b", corner_radius=10)
        self.params_frame.pack(fill="x", padx=15, pady=(15, 0), ipadx=10, ipady=10)

        self.params_title = ctk.CTkLabel(self.params_frame, text="AI HYPERPARAMETERS",
                                         font=ctk.CTkFont(size=12, weight="bold"), text_color="#94a3b8")
        self.params_title.pack(anchor="w", padx=10, pady=(0, 10))

        self.epoch_header = ctk.CTkFrame(self.params_frame, fg_color="transparent")
        self.epoch_header.pack(fill="x", padx=10)
        ctk.CTkLabel(self.epoch_header, text="Epochs", font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#e2e8f0").pack(side="left")
        self.epoch_val_label = ctk.CTkLabel(self.epoch_header, text="50", font=ctk.CTkFont(size=13, weight="bold"),
                                            text_color="#38bdf8")
        self.epoch_val_label.pack(side="right")

        self.epoch_slider = ctk.CTkSlider(self.params_frame, from_=10, to=200, number_of_steps=190,
                                          button_color="#38bdf8", button_hover_color="#0284c7",
                                          command=self.update_epoch_val)
        self.epoch_slider.set(50)
        self.epoch_slider.pack(fill="x", padx=10, pady=(5, 15))

        self.patience_header = ctk.CTkFrame(self.params_frame, fg_color="transparent")
        self.patience_header.pack(fill="x", padx=10)
        ctk.CTkLabel(self.patience_header, text="Patience", font=ctk.CTkFont(size=13, weight="bold"),
                     text_color="#e2e8f0").pack(side="left")
        self.patience_val_label = ctk.CTkLabel(self.patience_header, text="15",
                                               font=ctk.CTkFont(size=13, weight="bold"), text_color="#f43f5e")
        self.patience_val_label.pack(side="right")

        self.patience_slider = ctk.CTkSlider(self.params_frame, from_=10, to=50, number_of_steps=40,
                                             button_color="#f43f5e", button_hover_color="#e11d48",
                                             command=self.update_patience_val)
        self.patience_slider.set(15)
        self.patience_slider.pack(fill="x", padx=10, pady=(5, 10))

        self.tooltip_label = ctk.CTkLabel(self.params_frame, text="Hover over a setting to see what it does.",
                                          text_color="#64748b", font=ctk.CTkFont(size=12, slant="italic"))
        self.tooltip_label.pack(pady=(5, 0))

        self.epoch_slider.bind("<Enter>", lambda e: self.tooltip_label.configure(
            text="EPOCHS (10-200): How many times the AI reviews the data.\nHigher = Smarter but takes longer. 50 is balanced.",
            text_color="#38bdf8"))
        self.epoch_slider.bind("<Leave>",
                               lambda e: self.tooltip_label.configure(text="Hover over a setting to see what it does.",
                                                                      text_color="#64748b"))
        self.patience_slider.bind("<Enter>", lambda e: self.tooltip_label.configure(
            text="PATIENCE (10-50): Stops training early if the AI stops learning.\nPrevents memorization (overfitting). 15 is optimal.",
            text_color="#f43f5e"))
        self.patience_slider.bind("<Leave>", lambda e: self.tooltip_label.configure(
            text="Hover over a setting to see what it does.", text_color="#64748b"))

        self.graph_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.graph_frame.pack(fill="both", expand=True, padx=5, pady=5)

        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(6, 4.2), facecolor='#0f172a')

        for ax in (self.ax1, self.ax2):
            ax.set_facecolor('#1e293b')
            ax.tick_params(colors='white')
            for spine in ax.spines.values():
                spine.set_color('#334155')

        self.ax1.set_title("Top-1 Accuracy", color="#38bdf8", fontsize=10)
        self.ax2.set_title("Training Loss", color="#f43f5e", fontsize=10)

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        self.show_configuration_ui()

    def show_configuration_ui(self):
        self.term_header.grid_remove()
        self.status_box.grid_remove()
        self.left_frame.grid_rowconfigure(4, weight=0)
        self.class_lbl.grid()
        self.classes_inner_frame.grid()
        self.left_frame.grid_rowconfigure(2, weight=1)

    def show_terminal_ui(self):
        self.class_lbl.grid_remove()
        self.classes_inner_frame.grid_remove()
        self.left_frame.grid_rowconfigure(2, weight=0)
        self.term_header.grid()
        self.status_box.grid()
        self.left_frame.grid_rowconfigure(4, weight=1)

    def update_epoch_val(self, val):
        self.epoch_val_label.configure(text=f"{int(val)}")

    def update_patience_val(self, val):
        self.patience_val_label.configure(text=f"{int(val)}")

    def load_classes(self):
        for widget in self.classes_inner_frame.winfo_children():
            widget.destroy()
        self.class_vars.clear()

        if os.path.exists(BASE_DATA_DIR):
            classes = [d for d in os.listdir(BASE_DATA_DIR) if os.path.isdir(os.path.join(BASE_DATA_DIR, d))]
            if classes:
                for cls in classes:
                    img_dir = os.path.join(BASE_DATA_DIR, cls)
                    img_count = len([f for f in os.listdir(img_dir) if os.path.isfile(os.path.join(img_dir, f))])
                    var = tk.BooleanVar(value=True)
                    self.class_vars[cls] = var
                    display_text = f"{cls}  ({img_count} images)"
                    cb = ctk.CTkCheckBox(self.classes_inner_frame, text=display_text, variable=var,
                                         font=ctk.CTkFont(size=12), text_color="#e2e8f0", fg_color="#8b5cf6",
                                         hover_color="#a855f7")
                    cb.pack(anchor="w", pady=4, padx=10)
                return

        ctk.CTkLabel(self.classes_inner_frame, text="No scan data found yet.\nUse the web UI to save data.",
                     text_color="#64748b", font=ctk.CTkFont(size=11)).pack(pady=15)

    def log_msg(self, msg):
        self.status_box.configure(state="normal")
        self.status_box.insert("end", f"> {msg}\n")
        lines = int(self.status_box.index('end-1c').split('.')[0])
        if lines > 100:
            self.status_box.delete("1.0", f"{lines - 100}.0")
        self.status_box.see("end")
        self.status_box.configure(state="disabled")

    def request_safe_stop(self):
        if not self.stop_requested:
            print("[SAFE STOP TRACE] 1. 'Safe Stop' button clicked. Initiating request...")
            self.log_msg("⚠️ SAFE STOP INITIATED! Waiting for epoch to safely conclude...")
            self.btn_stop.configure(state="disabled", text="⏳ HALTING...")
            self.stop_requested = True
            print("[SAFE STOP TRACE] 1. stop_requested flag set to True.")

    def validate_and_balance_dataset(self):
        if not os.path.exists(BASE_DATA_DIR):
            messagebox.showerror("Error",
                                 f"Could not find '{BASE_DATA_DIR}'. Have you collected data in the main app yet?")
            return False

        selected_classes = [cls for cls, var in self.class_vars.items() if var.get()]

        if len(selected_classes) < 2:
            messagebox.showerror("Error", "You must tick at least 2 target specialists to train the Auto-Pilot.")
            return False

        counts = {}
        for cat in selected_classes:
            files = os.listdir(os.path.join(BASE_DATA_DIR, cat))
            counts[cat] = len(files)

        min_count = min(counts.values())
        max_count = max(counts.values())

        if min_count < 50:
            error_msg = "NOT ENOUGH DATA!\n\nEvery checked category requires a minimum of 50 images to prevent AI confusion.\n\nCurrent active counts:\n"
            for k, v in counts.items():
                error_msg += f"- {k}: {v} images\n"
            messagebox.showerror("Insufficient Data", error_msg)
            return False

        if min_count != max_count:
            warn_msg = (
                f"DATASET IMBALANCE DETECTED!\n\n"
                f"Your selected folders have uneven data (Lowest: {min_count}, Highest: {max_count}).\n\n"
                f"To prevent the AI from becoming biased, the Engine will automatically pick exactly {min_count} random images "
                f"from your selected folders for this training session.\n\n"
                f"Do you wish to continue?"
            )
            if not messagebox.askyesno("Imbalance Detected", warn_msg):
                return False

        self.show_terminal_ui()
        self.log_msg(f"Balancing active dataset to exactly {min_count} images per category...")

        if os.path.exists(BALANCED_DATA_DIR):
            shutil.rmtree(BALANCED_DATA_DIR)
        os.makedirs(BALANCED_DATA_DIR)

        for cat in selected_classes:
            cat_target_dir = os.path.join(BALANCED_DATA_DIR, cat)
            os.makedirs(cat_target_dir)

            all_files = os.listdir(os.path.join(BASE_DATA_DIR, cat))
            selected_files = random.sample(all_files, min_count)

            for file in selected_files:
                src = os.path.join(BASE_DATA_DIR, cat, file)
                dst = os.path.join(cat_target_dir, file)
                shutil.copy2(src, dst)

        self.log_msg("Active Dataset successfully balanced and staged.")
        return True

    def start_training_process(self):
        if not self.validate_and_balance_dataset():
            return

        warn1 = messagebox.askokcancel("System Warning",
                                       "⚠️ STOP BACKGROUND TASKS\n\nTraining an AI requires significant CPU/RAM. Please close heavy applications before continuing.")
        if not warn1:
            self.show_configuration_ui()
            return

        self.btn_train.configure(state="disabled", text="⏳ TRAINING IN PROGRESS...", fg_color="#475569",
                                 text_color="#94a3b8")
        self.btn_stop.configure(state="normal", text="🛑 SAFE STOP", fg_color="#e11d48", text_color="white")

        self.epoch_slider.configure(state="disabled")
        self.patience_slider.configure(state="disabled")

        self.stop_requested = False
        self.current_best_acc = 0.0

        self.acc_value.configure(text="--%")
        self.time_label.configure(text="EST. TIME REMAINING: CALCULATING...")
        self.training_start_time = time.time()

        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()

        self.epochs_history.clear()
        self.acc_history.clear()
        self.loss_history.clear()
        self.update_graph()

        self.log_msg("Initializing Neural Engine...")
        threading.Thread(target=self.train_worker, daemon=True).start()

    def train_worker(self):
        try:
            target_epochs = int(self.epoch_slider.get())
            target_patience = int(self.patience_slider.get())

            self.metric_queue.put({"log": "Loading YOLOv8 nano classification model..."})
            model = YOLO('yolov8n-cls.pt')

            def on_fit_epoch_end(trainer):
                if getattr(self, 'stop_requested', False):
                    print(
                        "[SAFE STOP TRACE] 2. PyTorch epoch hook intercepted 'stop_requested'. Forcing trainer.stop = True")
                    trainer.stop = True

                epoch = trainer.epoch + 1
                metrics = trainer.metrics

                raw_acc = metrics.get('metrics/accuracy_top1', 0.0)
                try:
                    acc_val = float(raw_acc.item()) if hasattr(raw_acc, 'item') else float(raw_acc)
                except Exception:
                    acc_val = 0.0

                if acc_val > getattr(self, 'current_best_acc', 0.0):
                    self.current_best_acc = acc_val

                loss_val = 0.0
                if trainer.tloss is not None:
                    try:
                        if hasattr(trainer.tloss, 'shape') and len(trainer.tloss.shape) == 0:
                            loss_val = float(trainer.tloss.item())
                        elif hasattr(trainer.tloss, '__getitem__'):
                            extracted_item = trainer.tloss[0]
                            loss_val = float(extracted_item.item()) if hasattr(extracted_item, 'item') else float(
                                extracted_item)
                        else:
                            loss_val = float(trainer.tloss)
                    except Exception:
                        loss_val = 0.0

                self.metric_queue.put(
                    {"epoch": epoch, "acc": acc_val, "loss": loss_val, "target_epochs": target_epochs})

            model.add_callback("on_fit_epoch_end", on_fit_epoch_end)

            self.metric_queue.put({"log": f"Initiating {target_epochs}-Epoch Deep Learning Sequence..."})

            project_dir = os.path.abspath("SmiloAi_AutoPilot")

            # Start Training (This blocks until finished or stopped)
            model.train(
                data=os.path.abspath(BALANCED_DATA_DIR),
                epochs=target_epochs,
                patience=target_patience,
                imgsz=224,
                batch=16,
                project=project_dir,
                name="latest_router",
                exist_ok=True,
                verbose=False,
                plots=False
            )

            print("[SAFE STOP TRACE] 3. model.train() execution loop has completed. Yielding back to Python.")
            print(f"[SAFE STOP TRACE] 4. Validating epoch history. Length: {len(self.epochs_history)}")

            # 🛡️ FATAL CHECK: Did they stop on Epoch 1?
            if len(self.epochs_history) == 0:
                print("[SAFE STOP TRACE] ❌ Epoch history is 0. Aborting save process.")
                self.metric_queue.put({"status": "ERROR",
                                       "msg": "Safe Stop triggered too early! You must wait for at least 1 epoch to complete before halting, otherwise no weights exist to save."})
                return

            # Find the best weights
            print("[SAFE STOP TRACE] 5. Beginning search for optimal best.pt weights...")
            best_pt_path = None
            try:
                if hasattr(model, 'trainer') and hasattr(model.trainer, 'best'):
                    best_pt_path = str(model.trainer.best)
                    print(f"[SAFE STOP TRACE] 5a. Found model.trainer.best path: {best_pt_path}")
            except Exception as e:
                print(f"[SAFE STOP TRACE] ⚠️ Error accessing model.trainer.best: {e}")

            if not best_pt_path or not os.path.exists(best_pt_path):
                print(
                    "[SAFE STOP TRACE] 5b. model.trainer.best is missing or invalid. Initiating recursive fallback scan...")
                # Fallback Recursive Search
                search_dirs = [os.path.abspath("runs"), os.path.abspath("SmiloAi_AutoPilot")]
                newest_pt = None
                newest_time = 0
                for sdir in search_dirs:
                    if os.path.exists(sdir):
                        for root, _, files in os.walk(sdir):
                            if "best.pt" in files:
                                full_p = os.path.join(root, "best.pt")
                                mtime = os.path.getmtime(full_p)
                                print(f"[SAFE STOP TRACE] Found candidate: {full_p} (mtime: {mtime})")
                                if mtime > newest_time:
                                    newest_time = mtime
                                    newest_pt = full_p
                best_pt_path = newest_pt
                print(f"[SAFE STOP TRACE] 5c. Fallback scan selected path: {best_pt_path}")

            if best_pt_path and os.path.exists(best_pt_path):
                print(
                    f"[SAFE STOP TRACE] 6. Queueing 'READY_FOR_EXPORT' signal to GUI thread with path: {best_pt_path}")
                # ✨ THE ULTIMATE FIX: BOUNCE EXPORT TASK TO MAIN THREAD! ✨
                self.metric_queue.put({
                    "status": "READY_FOR_EXPORT",
                    "best_pt": best_pt_path,
                    "target_epochs": target_epochs
                })
            else:
                print("[SAFE STOP TRACE] ❌ FAILED to locate best.pt!")
                self.metric_queue.put({"status": "ERROR", "msg": "Could not locate best.pt weights after training!"})

        except Exception as e:
            print(f"[SAFE STOP TRACE] ❌ MASTER EXCEPTION IN BACKGROUND THREAD: {str(e)}")
            self.metric_queue.put({"status": "ERROR", "msg": f"Training failed: {str(e)}"})

    def unlock_ui_post_train(self):
        self.btn_train.configure(state="normal", text="INITIATE TRAINING", fg_color="#8b5cf6", text_color="white")
        self.btn_stop.configure(state="disabled", text="🛑 SAFE STOP", fg_color="#475569")
        self.epoch_slider.configure(state="normal")
        self.patience_slider.configure(state="normal")
        self.progress_bar.set(1.0)
        self.show_configuration_ui()
        self.load_classes()

    def check_queue(self):
        while not self.metric_queue.empty():
            data = self.metric_queue.get()

            if "log" in data:
                self.log_msg(data["log"])

            # ✨ THE SYNTAX FIX IS HERE: `elif` chained perfectly back to `if`
            elif data.get("status") == "READY_FOR_EXPORT":
                print("[SAFE STOP TRACE] 7. GUI Thread intercepted 'READY_FOR_EXPORT'. Commencing safe extraction.")
                self.btn_stop.configure(text="⏳ EXPORTING TO ONNX...", state="disabled")
                self.log_msg("Optimal weights located.")
                self.log_msg("Optimizing model: Converting to ONNX format...")

                self.update()

                best_pt_path = data["best_pt"]
                target_epochs = data["target_epochs"]

                try:
                    print(f"[SAFE STOP TRACE] 8. Instantiating fresh YOLO object from path: {best_pt_path}")
                    best_model = YOLO(best_pt_path)

                    print(
                        "[SAFE STOP TRACE] 9. Executing best_model.export(format='onnx')... THIS MIGHT CAUSE A SILENT CRASH!")
                    exported_path = best_model.export(format="onnx", imgsz=224)
                    print(f"[SAFE STOP TRACE] 10. ONNX export successfully returned path: {exported_path}")

                    final_model_name = "Unknown"
                    if exported_path and os.path.exists(str(exported_path)):
                        print("[SAFE STOP TRACE] 11. ONNX file verified on disk. Generating dynamic filename...")
                        os.makedirs(AUTOPILOT_OUT_DIR, exist_ok=True)

                        safe_best_acc = float(getattr(self, 'current_best_acc', 0.0))
                        best_acc_int = round(safe_best_acc * 100)
                        version_str = time.strftime("%Y%m%d_%H%M%S")
                        final_model_name = f"AUTOPILOT_{best_acc_int:02d}_{version_str}.onnx"
                        final_dest = os.path.join(AUTOPILOT_OUT_DIR, final_model_name)

                        print(f"[SAFE STOP TRACE] 12. Moving exported ONNX to final destination: {final_dest}")
                        shutil.move(str(exported_path), final_dest)
                        self.log_msg(f"✅ ONNX Export complete: {final_model_name}")

                        self.log_msg("Cleaning up heavy PyTorch (.pt) checkpoint files...")
                        try:
                            weights_dir = os.path.dirname(best_pt_path)
                            for f in os.listdir(weights_dir):
                                if f.endswith('.pt'):
                                    os.remove(os.path.join(weights_dir, f))
                        except Exception as cleanup_err:
                            print(f"[SAFE STOP TRACE] ⚠️ Minor cleanup warning: {cleanup_err}")
                            pass

                        print(
                            f"[SAFE STOP TRACE] 13. Preparing final UI status messages. stop_requested={getattr(self, 'stop_requested', False)}")
                        if getattr(self, 'stop_requested', False):
                            self.metric_queue.put({"status": "STOPPED", "file": final_model_name})
                        else:
                            final_epoch = len(self.epochs_history)
                            if final_epoch > 0 and final_epoch < target_epochs:
                                self.metric_queue.put(
                                    {"status": "EARLY_STOP", "epoch": final_epoch, "file": final_model_name})
                            else:
                                self.metric_queue.put({"status": "DONE", "file": final_model_name})

                    else:
                        print("[SAFE STOP TRACE] ❌ Export path returned success, but file does not exist on disk!")
                        self.metric_queue.put(
                            {"status": "ERROR", "msg": "Export returned success but the ONNX file was missing."})
                except Exception as export_err:
                    print(f"[SAFE STOP TRACE] ❌ EXCEPTION CAUGHT DURING EXPORT: {export_err}")
                    print(traceback.format_exc())
                    self.metric_queue.put({"status": "ERROR", "msg": f"Failed to export to ONNX: {str(export_err)}"})

            elif "status" in data:
                self.progress_bar.stop()
                self.progress_bar.configure(mode="determinate")
                model_file = data.get("file", "unknown_model.onnx")

                if data["status"] == "DONE":
                    self.time_label.configure(text="EST. TIME REMAINING: 0m 0s (FINISHED)")
                    self.log_msg("✅ TRAINING COMPLETE! Model saved.")
                    messagebox.showinfo("Success",
                                        f"Auto-Pilot has been successfully trained!\n\n'{model_file}'\nis located in the AUTOPILOT/AUTOPILOT_MODELS folder and ready for the main engine.")
                    self.unlock_ui_post_train()

                elif data["status"] == "EARLY_STOP":
                    self.time_label.configure(text="EST. TIME REMAINING: 0m 0s (FINISHED)")
                    final_epoch = data.get("epoch", "unknown")
                    self.log_msg(f"🛑 EARLY STOPPING AT EPOCH {final_epoch}.")
                    self.log_msg("The model stopped improving, so training was halted to prevent overfitting.")
                    messagebox.showinfo("Early Stopping",
                                        f"Training converged early at epoch {final_epoch}!\n\nThe best weights have been compiled into:\n'{model_file}'")
                    self.unlock_ui_post_train()

                elif data["status"] == "STOPPED":
                    self.time_label.configure(text="EST. TIME REMAINING: --:-- (HALTED)")
                    self.log_msg("🛑 TRAINING HALTED SAFELY.")
                    messagebox.showinfo("Stopped",
                                        f"Training was safely interrupted.\nProgress up to the last completed epoch has been saved as:\n'{model_file}'")
                    self.unlock_ui_post_train()

                elif data["status"] == "ERROR":
                    self.time_label.configure(text="EST. TIME REMAINING: --:-- (ERROR)")
                    self.log_msg(f"❌ FATAL ERROR: {data['msg']}")
                    messagebox.showerror("Training Failed", str(data['msg']))
                    self.unlock_ui_post_train()

            elif "epoch" in data:
                if self.progress_bar.cget("mode") == "indeterminate":
                    self.progress_bar.stop()
                    self.progress_bar.configure(mode="determinate")

                epoch = data["epoch"]
                acc = data["acc"]
                loss = data["loss"]
                target_epochs = data["target_epochs"]

                self.epochs_history.append(epoch)
                self.acc_history.append(acc)
                self.loss_history.append(loss)

                self.log_msg(f"Epoch {epoch}/{target_epochs} -> Acc: {acc:.4f} | Loss: {loss:.4f}")
                self.acc_value.configure(text=f"{acc * 100:.1f}%")

                elapsed_time = time.time() - getattr(self, 'training_start_time', time.time())
                if epoch > 0:
                    time_per_epoch = elapsed_time / epoch
                    remaining_epochs = target_epochs - epoch
                    est_remaining_sec = int(time_per_epoch * remaining_epochs)
                    mins, secs = divmod(est_remaining_sec, 60)
                    self.time_label.configure(text=f"EST. TIME REMAINING: {mins}m {secs}s")

                self.progress_bar.set(min(1.0, epoch / float(target_epochs)))
                self.update_graph()

        self.after(500, self.check_queue)

    def update_graph(self):
        self.ax1.clear()
        self.ax2.clear()

        self.ax1.set_title("Top-1 Accuracy", color="#38bdf8", fontsize=10)
        self.ax2.set_title("Training Loss", color="#f43f5e", fontsize=10)

        if self.epochs_history:
            self.ax1.plot(self.epochs_history, self.acc_history, color="#38bdf8", marker='o', markersize=3, linewidth=2)
            self.ax2.plot(self.epochs_history, self.loss_history, color="#f43f5e", marker='o', markersize=3,
                          linewidth=2)

            self.ax1.fill_between(self.epochs_history, self.acc_history, alpha=0.2, color="#38bdf8")
            self.ax2.fill_between(self.epochs_history, self.loss_history, alpha=0.2, color="#f43f5e")

        self.fig.tight_layout()
        self.canvas.draw()


if __name__ == "__main__":
    app = AutoPilotTrainer()

    if pyi_splash and pyi_splash.is_alive():
        pyi_splash.close()

    # ✨ THE FIX: Force Windows to show the app normally, not minimized!
    app.deiconify()  # Restore from taskbar if minimized
    app.lift()  # Bring to the top of the window stack
    app.attributes('-topmost', True)  # Force it above all other apps momentarily
    app.update()  # Let the OS process the command
    app.attributes('-topmost', False)  # Return to normal behavior so it doesn't block other apps
    app.focus_force()  # Grab keyboard and mouse focus

    app.mainloop()