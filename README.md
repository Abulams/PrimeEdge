# PrimeEdge (Market-OS)

Institutional-grade quantitative FX/commodities trading platform and statistical edge intelligence system.

Live Production: **[https://primeedge.app](https://primeedge.app)**  
Architecture: **Linux VPS (Linode Ubuntu) + FastAPI / Gunicorn + cTrader OpenAPI v2 + MQL5 EA Bridge + Caddy**

---

## 1. System Overview

PrimeEdge delivers empirical probability-weighted trade setups across major FX pairs and commodities (`EURUSD`, `GBPUSD`, `AUDUSD`, `USDJPY`, `XAUUSD`). It computes statistical corridor distributions (P25/P50/P75/P90), Maximum Adverse Excursion (MAE), Maximum Favorable Excursion (MFE), and macro regime overlays (DXY, VIX) with zero look-ahead bias.

### Key Capabilities
- **Quantitative Signal Engine (V4)**: Point-in-time empirical distributions with multi-session reference anchoring (T₀) and continuous corridor validation.
- **Direct cTrader Execution**: Native cTrader OpenAPI v2 TCP engine for real-time order execution and multi-client trade copying with client risk guardrails.
- **MQL5 EA Remote Bridge**: Zero-polling HTTP execution bridge for self-hosted client MT5 terminals.
- **AI Analyst Engine**: Natural language reasoning interface (Gemini LLM) grounded strictly in deterministic quantitative tool outputs.
- **Institutional Telemetry & Alerts**: Automated Telegram signal dispatch with dynamically rendered Pillow visual cards and rich macro context.

---

## 2. Architecture & Components

```
                ┌──────────────────────────────────────────────┐
                │             Caddy Reverse Proxy              │
                │        (primeedge.app, ops.primeedge.app)    │
                └──────────────────────┬───────────────────────┘
                                       │
                                       ▼
                ┌──────────────────────────────────────────────┐
                │        FastAPI Application (Gunicorn)        │
                │      - Quant Engines (V4 Signals & Scenarios)│
                │      - User & Broker Account Management      │
                │      - AI Analyst Engine                     │
                │      - Telegram Notification Service         │
                └──────────────┬───────────────────────────────┘
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
 ┌──────────────────────┐              ┌──────────────────────┐
 │   cTrader Copier     │              │    MQL5 EA Bridge    │
 │ (Twisted TCP v2)     │              │  (/api/v1/execution) │
 │ Direct copy to client│              │ Polled by client EAs │
 │ cTrader accounts     │              │ on remote terminals  │
 └──────────────────────┘              └──────────────────────┘
```

---

## 3. Technology Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy, SQLite (production/staging), Gunicorn (`uvicorn.workers.UvicornWorker`)
- **Web & Proxy**: Caddy (automatic SSL, zero-config reverse proxy)
- **Execution**:
  - `cTrader OpenAPI v2`: Protobuf TCP stream (`ctrader_gateway.py`, `ctrader_copier_service.py`)
  - `MQL5 Bridge`: REST endpoint polling (`ea_bridge_router.py`, `MarketOS_Bridge.mq5`)
- **Frontend**: Single-Page App built with Vite + React + Tailwind CSS (compiled static assets served from `frontend/dist`)
- **Database**: SQLite / PostgreSQL compatible SQLAlchemy models

---

## 4. Local Development Setup

### Prerequisites
- Python 3.11+
- Git

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/Abulamido/Market-OS.git
   cd Market-OS
   ```
2. Set up virtual environment and install dependencies:
   ```bash
   python -m venv venv
   # Linux/macOS:
   source venv/bin/activate
   # Windows:
   .\venv\Scripts\Activate.ps1

   pip install -r requirements_full.txt
   ```
3. Configure environment:
   ```bash
   cp .env.example backend/.env
   # Edit backend/.env with your local credentials and paths
   ```
4. Run the local backend:
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload --port 8000
   ```
5. Access the API and UI at `http://localhost:8000`.

---

## 5. Deployment Pipeline

Deployments target the Linode production server (`172.237.112.138`) at `/var/www/market-os`:

```bash
# Standard deploy (rsync backend + restart systemd service)
./deploy.sh

# Deploy with database migrations
./deploy.sh --migrate

# Full deployment (including static assets)
./deploy.sh --full
```

Or via `make`:
```bash
make deploy
make health
```

---

## 6. Directory Structure

```
Market-OS/
├── backend/
│   ├── app/
│   │   ├── execution/        # cTrader gateway & copier, bridge manager
│   │   ├── routers/          # FastAPI REST endpoints
│   │   ├── analyst_engine.py # AI Analyst LLM reasoning & tools
│   │   ├── telegram_service.py # Signal card generator & Telegram bot
│   │   ├── models.py         # SQLAlchemy ORM models
│   │   └── main.py           # Application entrypoint & lifespan
│   └── tests/                # Pytest unit & regression tests
├── frontend/
│   └── dist/                 # Pre-compiled static assets served by FastAPI
├── mql5/
│   ├── MarketOS_Bridge.mq5   # Canonical MQL5 Expert Advisor source
│   └── MarketOS_Bridge.ex5   # Compiled MT5 binary for remote bridge
├── archive/
│   ├── windows_worker/       # Retired Windows MT5 multi-terminal scripts
│   └── windows_scripts/      # Retired Windows batch & supervisor scripts
├── docs/
│   └── archive/              # Diagnostic reports and legacy phase research
├── deploy.sh                 # Canonical production deployment script
├── Makefile                  # Local workflow and deployment targets
└── Caddyfile                 # Production reverse proxy configuration
```
