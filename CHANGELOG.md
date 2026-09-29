# Changelog

All notable changes to the SmiloAI project will be documented in this file.

## [6.0.0] - 2026-09-30

### Added
- **Native Desktop App Integration**: Converted the browser-based web application into a fully native Desktop Standalone App Mode using Chromium hooks, featuring proper OS taskbar integration and automated backend shutdown when the UI window is closed.
- **Multi-Device Mobile Syncing**: Introduced dynamic QR Code syncing, allowing users to connect their mobile devices on the same network to capture and instantly sync clinical photos to the desktop workstation.
- **"Dental Position" Anatomical Mapping**: Integrated the `DENTALPOSITION` AI model specifically for identifying precise tooth locations (e.g., Central Incisor, Molar).
- **Intelligent Anatomical Parsing**: Wrote custom software logic to dynamically categorize raw AI detections into precise anatomical identifiers (e.g., *Maxillary Right Central Incisor*) based on jaw context.
- **Comprehensive PDF Export Engine**: Completely rebuilt the clinical report generator to produce highly formal HTML-to-PDF clinical records.
- **FDI & Universal Numbering**: Integrated standard dental numbering systems into the granular flaw analysis reports.
- **Background PDF Processing**: Replaced instant HTML popups with a seamless background PDF generation workflow featuring live progress updates in the UI.

### Changed
- **UI/UX Glassmorphism Overhaul**: Transitioned the entire frontend from a basic layout to a premium glassmorphic dark-mode aesthetic with dynamic amber and emerald status accents.
- **Liquid Pipeline Visualizer**: Redesigned the Active Flow execution visualizer to feature "liquid glass" rounded corners and dynamic model node names.
- **Global Typography Modernization**: Ripped out generic web fonts in favor of sleek, modern typography across the entire interface and PDF reports.
- **Smart Model Downloading**: Modified the cloud model synchronization to sync the available model registry instantly without freezing the application, streamlining the massive `.onnx` downloads with live progress bars.
- **Report Grouping Logic**: Grouped adjacent tooth flaws (e.g., a cavity spanning two incisors) into single logical findings in the clinical summary rather than duplicating false entries.

### Fixed
- **Critical Security Patches**: Patched critical Path Traversal vulnerabilities in model loading and deleting endpoints that previously allowed arbitrary file access.
- **Hardened Endpoints**: Locked down unauthenticated destructive endpoints (e.g., `/shutdown`) to prevent Denial of Service attacks.
- **CORS & HTTP Stabilisation**: Fixed overly permissive CORS configurations and added strict HTTP timeouts to prevent the backend from infinitely hanging during failed requests.
- **Connection Diagnostics**: Fixed bugs causing the mobile camera sync to infinitely load, and added explicit connection diagnostic logs in the terminal.
- **PDF Page Breaking**: Resolved severe formatting bugs in PDF exports where images were cut off or stranded on empty pages by enforcing intelligent 4-images-per-page CSS pagination constraints.
