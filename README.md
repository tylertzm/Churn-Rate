# Churn Intelligence Dashboard | SumUp Enterprise


WIP.

## 🛠️ Architecture

The system is built on a modular Python/React stack with Docker containerization:

- **Backend:** FastAPI (Modular Orchestration Engine) - serves both API and static frontend
- **Frontend:** React 18 + Tailwind CSS (High-Density UI) - served statically by FastAPI
- **Data:** CSV-based single source of truth for high-performance retrieval.
- **Containerization:** Docker for easy deployment and environment consistency

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
└── backend_api.py          # Enterprise API (serves frontend statically)
frontend/
└── index.html              # Intelligence Interface (served by backend)
Dockerfile                  # Docker containerization
requirements.txt            # Python dependencies
```

---

## 🏃 Getting Started

### Quick Start with Docker (Recommended)
```bash
# Build the Docker image
docker build -t churn-rate .

# Run the container
docker run -p 8000:8000 churn-rate
```

Then open http://localhost:8000 in your browser to access the dashboard.

### Local Development Setup

#### 1. Requirements
Ensure you have the following installed:
- Python 3.11+
- Playwright (Headless/Headful Chromium)

#### 2. Installation
```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium
```

#### 3. Execution
To launch the full intelligence hub:

**Launch Backend (includes frontend):**
```bash
cd backend
python backend_api.py
```
*Runs on `http://localhost:8000`* (both API and frontend)

---

## 🔄 Data Lifecycle
- **Manual Sync:** Click the **"Refresh Data"** button in the dashboard header to trigger a full real-time re-scrape and analysis cycle.
- **Analysis Only:** The dashboard automatically performs in-memory filtering and statistics calculation on the latest dataset upon every load.
---
*© 2026 Churn Intelligence Hub. For institutional use only.*
