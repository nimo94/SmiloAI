# SmiloAI Engine v6.0 — Offline-First, Dual-Modality Dental AI Diagnostic Workstation

<p align="center">
  <img src="Sourcecodes/logo.png" width="150" alt="SmiloAI Logo">
</p>

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-00a393.svg)](https://fastapi.tiangolo.com)
[![ONNX Runtime](https://img.shields.io/badge/ONNX%20Runtime-CPU%20Inference-005ced.svg)](https://onnxruntime.ai/)
[![Ultralytics YOLO](https://img.shields.io/badge/Ultralytics-YOLOv8-blueviolet.svg)](https://ultralytics.com)
[![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-1f6feb.svg)](https://github.com/TomSchimansky/CustomTkinter)

---

## 🌟 Overview (What's New in v6.0)

**SmiloAI Engine v6.0** introduces a massive leap forward in both security, user experience, and clinical reporting compared to v5.0. It transforms the engine from a local browser app into a polished, standalone Desktop Application while overhauling the diagnostic PDF reporting system for enterprise clinical use.

### 📊 v5.0 vs v6.0 Comparison

| Feature | SmiloAI v5.0 | SmiloAI v6.0 |
| :--- | :--- | :--- |
| **User Interface** | Standard Web Browser UI | **Native Standalone Desktop App** with Taskbar Integration |
| **Design Language** | Basic HTML/CSS layouts | **Premium Glassmorphism** with dynamic UI accents & typography |
| **Camera Sync** | None (Manual Uploads only) | **Live QR Mobile Sync** for instant smartphone photo capture |
| **Pipeline Visuals** | Static execution nodes | **"Liquid Glass" Animations** with live diagnostic node mapping |
| **Security Architecture**| Vulnerable to path traversal | **Fully Patched & Hardened** endpoints with HTTP timeouts |
| **Anatomical Mapping** | Basic Bounding Boxes | **Dental Position Matrix** (e.g., *Maxillary Right Central Incisor*) |
| **Clinical Export** | Basic HTML popups | **Formal PDF Reports** (Universal Numbering, Smart Pagination) |

### 🔥 Detailed v6.0 Upgrades:
- **Core Security Patches**: Complete patching of arbitrary file read/write vulnerabilities (path traversals) and unauthenticated destructive endpoints.
- **Multi-Device Camera Sync**: Advanced mobile QR code syncing allowing users to capture clinical photos directly from their smartphone and sync them flawlessly to the desktop application, complete with connection diagnostics.
- **Standalone App Transformation**: The web UI now launches as a Native Standalone Desktop App (using Chromium App Mode) featuring proper OS taskbar integration and graceful backend shutdown when closed.
- **UI/UX Glassmorphism**: A total UI redesign featuring premium glassmorphism, dynamic amber/emerald accents, sleek modern typography, and a "liquid glass" execution visualizer for the AI pipelines.
- **Dental Position Anatomical Mapping**: Integration of the specialized `DENTALPOSITION` model with custom logic to map raw detections into precise anatomical labels (e.g., *Maxillary Right Central Incisor*) and group multi-tooth flaws logically in summaries.
- **Comprehensive PDF Reporting**: A totally rebuilt PDF generation engine that produces highly formal clinical reports with FDI/Universal tooth numbering, intelligent 4-image-per-page formatting, and seamless background exporting.

---

## 🧠 Core AI Specialist Models & Confidence Architecture

SmiloAI v6.0 retains its automated, modular model management architecture. Models are loaded directly from the local filesystem (`/Sourcecodes/model/`) into memory via **ONNX Runtime** and **Ultralytics YOLOv8**, optimized for CPU inference with AVX2 instruction acceleration.

### 📦 Bundled & Supported Specialist Models

| Model Filename | Diagnostic Specialty | Modality | Benchmark Confidence / Accuracy | Description |
| :--- | :--- | :--- | :--- | :--- |
| `CALCULUSMD_R_60.onnx` | **Dental Calculus & Tartar** | `RGB` (Intraoral Photo) | **60% (`R_60`)** top-1 mAP | Detects mineralized plaque (calculus/tartar) build-up along gum lines and interproximal tooth surfaces. |
| `CARIESMD_XR_95.onnx` *(Example)* | **Dental Caries (Cavities)** | `X-Ray` (Radiograph) | **95% (`XR_95`)** top-1 mAP | Identifies enamel erosion, dentin decay, and interproximal cavities on bitewing/periapical radiographs. |
| `GINGIVITISMD_R_85.onnx` *(Example)* | **Gingival Inflammation** | `RGB` (Intraoral Photo) | **85% (`R_85`)** top-1 mAP | Segments gingival margins and analyzes marginal redness/swelling to detect periodontal inflammation. |
| `DENTALPOSITION_R_98.onnx` | **Anatomical Mapping** | `RGB` (Intraoral Photo) | **98% (`R_98`)** top-1 mAP | Specifically identifies tooth locations (e.g. Central Incisor, Molar) to provide spatial context for clinical reports. |

### 🔍 Automated Model Naming & Discovery Protocol

When any model file (`.onnx` or `.pt`) is placed in the model directory, the engine parses it according to the standard convention:
```
{DiagnosticName}MD_{ModalityCode}_{ConfidenceScore}.{Extension}
```
- **Diagnostic Name**: Identifies the pathology. The trailing `MD` designates a Medical Diagnostic specialist.
- **Modality Code**: `_R_` (RGB) or `_XR_` (X-Ray).
- **Confidence / Accuracy Score**: The numerical benchmark score automatically displayed in the UI Model Manager.

---

## ✈️ Auto-Pilot Smart Routing Engine

A breakthrough feature in SmiloAI is the **Auto-Pilot Smart Router**—a self-training classification pipeline that dynamically inspects incoming patient scans and routes them to the optimal custom diagnostic workflow automatically.

### 🛠️ Built-In Desktop Training Suite (`auto_pilot_trainer.py`)
SmiloAI includes an integrated desktop training application built with **CustomTkinter**, **PyTorch**, and **Matplotlib**. Clinicians and engineers can train new routing models directly on their workstation, exporting them as ONNX format (`AUTOPILOT_{accuracy}_{YYYYMMDD_HHMMSS}.onnx`).

---

## 🩺 Dual-Modality Diagnostic Capabilities

### 📸 Intraoral RGB Photography (`RGB`)
- **Tooth Decay & Cavities**: Discoloration tracking and surface cavitation detection.
- **Plaque & Calculus Deposits**: Edge-detection for mineralized tartar along gingival margins.
- **Gingivitis & Soft Tissue**: Color-space normalization for gingival redness and inflammation.

### 🩻 Radiographic X-Ray Analysis (`X-Ray`)
- **Sub-Surface Caries**: Interproximal and recurrent decay detection.
- **Periodontal Bone Loss**: Alveolar crest level evaluation.
- **Periapical Lesions**: Radiolucency detection around root apices indicating infection.

---

## ⚡ Advanced Inference Pipelines & Flow Builder

SmiloAI provides flexible inference execution modes tailored for different clinical workflows:
1. **Single & Batch Scan Mode**: Real-time screening of individual patient photos or high-throughput batch processing.
2. **Sequential Specialist Mode**: Chains multiple specialist models sequentially.
3. **Custom Flow Graph Editor**: An interactive visual node-wiring canvas to build custom diagnostic pipelines utilizing a Breadth-First Search (BFS) graph traversal engine.

---

## 🎛️ Confidence Thresholding & IoU NMS Filtering

- **Dynamic Confidence Control (`conf_threshold`)**: A real-time UI slider (defaulting to `0.25`) to calibrate model sensitivity.
- **IoU-Based Non-Maximum Suppression (NMS)**: Eliminates duplicate bounding boxes across multiple models using an IoU threshold of `0.4`.

---

## 🎨 Heads-Up Display (HUD) & Clinical Reporting

SmiloAI generates rich visual diagnostics:
- **Luminance Halo Annotations**: Bounding boxes with soft Gaussian-blurred glow layers for universal readability.
- **Comprehensive PDF Reports (New in v6)**: A completely redesigned HTML-to-PDF export pipeline utilizing Universal and FDI numbering systems, organized spatial mapping, and highly-detailed crop analyses for clinical documentation.

---

## 🤖 AI Clinical Assistant (LLM Integration)

SmiloAI integrates an optional **AI Clinical Assistant** powered by a high-speed streaming LLM API:
- **Server-Sent Events (SSE) Streaming**: Delivers token-by-token real-time narrative summaries via `/generate_ai_summary_stream`.
- **Context-Aware Translation**: Translates technical bounding box coordinates into empathetic, patient-friendly clinical treatment explanations.

---

## 🚀 Installation & Setup Guide

### 📋 System Requirements
- **Operating System**: Windows 10/11 (64-bit), Linux, or macOS.
- **Processor**: Intel Core i5 6th Gen / AMD Ryzen 3 or newer (**AVX2 instruction support required**).
- **RAM**: 8 GB minimum (16 GB recommended).
- **Python**: Python 3.10 or newer.

### ⚡ Quick Start (Developer Setup)

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/nimo94/SmiloAI.git
   cd SmiloAI
   ```

2. **Create & Activate Virtual Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install Required Dependencies**:
   ```bash
   pip install --upgrade pip
   pip install fastapi uvicorn opencv-python ultralytics torch torchvision pillow numpy groq requests customtkinter matplotlib pandas
   ```

4. **Launch SmiloAI Workstation**:
   ```bash
   cd Sourcecodes
   python main.py
   ```
   *The FastAPI server will initialize and automatically launch the Native Desktop App UI!*

---

## 🔒 Security & Privacy Notice

SmiloAI v6.0 is designed from the ground up as an **offline-first medical workstation**:
- **Zero Data Exfiltration**: Patient photographs and X-ray scans are processed entirely locally in your machine's system memory. No patient image data is transmitted to the internet.
- **Optional Cloud Features**: External network communication only occurs if explicitly configured (e.g., transmitting anonymized text summaries for LLM reports).

---

## ⚠️ Clinical Disclaimer

SmiloAI is engineered as an advanced AI-assisted supplementary screening tool for educational, diagnostic research, and oral health awareness purposes. **It is not a substitute for professional clinical judgment, formal radiological diagnosis, or specialized dental examinations.** All diagnostic findings should be verified by a qualified dental surgeon prior to initiating clinical treatment.

---

## 📄 License & Author

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

**Copyright (c) 2025–2026 Aswindra Selvam**  
*SmiloAI v6.0 — Final Year Project Technical Submission*
