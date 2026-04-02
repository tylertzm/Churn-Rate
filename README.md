# Churn Intelligence Dashboard | SumUp Enterprise

A high-performance, modular intelligence command center designed to monitor merchant sentiment, identify churn risks, and coordinate proactive outreach.

---

## 🚀 Key Features

- **Enterprise Modern UI:** High-density, Bloomberg-style dashboard with 1px Slate borders, SumUp Blue branding, and institutional typography.
- **Automated AI Pipeline:** Integrated 3-step modular orchestration:
  - **Modular Scraper:** High-speed Trustpilot ingestion with pagination and state persistence.
  - **Normalization Engine:** Automated data cleaning and multi-line review reconstruction.
  - **AI Churn Inference:** Advanced rating-to-risk mapping and high-value business detection.
- **On-Demand Intelligence:** Real-time data synchronization with active loading feedback and relative "Last Synced" audit logs.
- **Action Registry:** Critical outreach prioritization lists for high-value merchants.

---

## 🛠️ Architecture

The system is built on a modular Python/React stack:

- **Backend:** FastAPI (Modular Orchestration Engine)
- **Frontend:** React 18 + Tailwind CSS (High-Density UI)
- **Data:** CSV-based single source of truth for high-performance retrieval.

### Project Structure
```text
backend/
├── scraping/
│   └── trustpilot/
│       ├── scrape.py       # Modular Scraper
│       └── reviews.csv     # Raw Scrape Data
├── preprocessing/
│   └── cleaning.py         # Data Normalization
├── statistics/
│   ├── churn_rate.py       # AI Inference Engine
│   └── reviews_churn_added.csv # Single Source of Truth
└── backend_api.py          # Enterprise API
frontend/
└── index.html              # Intelligence Interface
```

---

## 🏃 Getting Started

### 1. Requirements
Ensure you have the following installed:
- Python 3.11+
- Playwright (Headless/Headful Chromium)

### 2. Installation
```bash
# Install dependencies
pip install fastapi uvicorn pandas dateparser playwright
playwright install chromium
```

### 3. Execution
To launch the full intelligence hub:

kill -9 $(lsof -t -i:8000) $(lsof -t -i:3000) || true to shut down both
**Launch Backend:**
```bash
cd backend
python backend_api.py
```
*Runs on `http://localhost:8000`*

**Launch Frontend:**
```bash
cd frontend
python3 -m http.server 3000
```
*Runs on `http://localhost:3000`*

---

## 🔄 Data Lifecycle
- **Manual Sync:** Click the **"Refresh Data"** button in the dashboard header to trigger a full real-time re-scrape and analysis cycle.
- **Analysis Only:** The dashboard automatically performs in-memory filtering and statistics calculation on the latest dataset upon every load.

---
*© 2026 Churn Intelligence Hub. For institutional use only.*
