# Matrimony AI Extraction & Analytics Portal

A full-stack Flask application for extracting, staging, managing, and exporting matrimonial candidate profiles using Gemini 2.5 Flash OCR with full Tamil character support.

## Features
- **AI Profile Scanning**: Extracts multi-profile classified newspaper cutouts.
- **Continuous Accumulation**: Append multiple photos into staging without overwriting previous uploads.
- **Analytics Dashboard**: Real-time metric cards and interactive Chart.js charts.
- **Universal Export**: Export filtered data to CSV (UTF-8 BOM), Excel (.xlsx), and PDF (with Noto Sans Tamil Unicode).
- **Batch Tracking**: Automatic sequential IDs (`SMMOC01`, `SMMOC02`, etc.).

## Quick Start
1. Clone the repository:
   ```bash
   git clone [https://github.com/](https://github.com/)<your-username>/matrimony-portal.git
   cd matrimony-portal