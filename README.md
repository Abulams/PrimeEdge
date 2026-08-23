# Market OS

> **Private repository — authorised contributors only.**

An institutional-grade execution and decision intelligence platform for active FX and commodities traders. Market OS combines real-time macro regime analysis, structured trade planning, cloud-native MT5 auto-execution, and a forensic replay engine into a single, unified interface.

---

## Modules

| Module | Description |
|---|---|
| **FIND (Radar)** | Real-time macro regime detection — DXY, VIX, US10Y, currency strength matrix, instrument DNA profiling |
| **PLAN (Cockpit)** | Structured trade planning with R-based risk sizing, entry logic, invalidation and target levels |
| **EXECUTION (Bridge)** | Cloud MT5 execution — zero-install auto-execution via encrypted broker account connection, per-account killswitches, MAE/MFE guardrails |
| **Auto-Journal** | Automatic trade journaling with performance analytics, R-multiple tracking, and session tagging |
| **WHY (Evidence)** | Historical evidence scoring — surfaces similar market days ranked by structural similarity |
| **REPLAY (Simulation)** | Batch simulation engine for hypothesis testing and strategy validation |
| **AI Analyst** | Contextual market narrative generation and pattern interpretation |

---

## Stack

**Backend:** Python 3.11 · FastAPI · SQLAlchemy · SQLite · JWT Auth  
**Frontend:** React 18 · TypeScript · Vite · Native CSS (no Tailwind)  
**Execution:** MT5 native connector · Cloud execution router · AES-256 credential encryption  
**Deployment:** Cloudflare Tunnel · Windows host · Single-port (8000) serving

---

## Project Structure

```
market-os/
├── backend/
│   └── app/
│       ├── main.py                  # FastAPI app + static file serving
│       ├── auth.py                  # JWT + bcrypt auth
│       ├── models.py                # SQLAlchemy models
│       ├── routers/
│       │   ├── auth_router.py       # Register / login / refresh / me
│       │   └── execution_cloud_router.py  # Cloud execution API
│       └── execution/
│           ├── cloud_router.py      # Multi-tenant execution router
│           ├── crypto.py            # AES-256 credential encryption
│           ├── mt5_client.py        # MT5 native connector
│           └── bridge_manager.py   # Local execution bridge
├── frontend/
│   └── src/
│       ├── App.tsx                  # Main app shell + auth gate
│       ├── AuthContext.tsx          # JWT session management
│       ├── LoginPage.tsx            # Institutional login UI
│       └── ExecutionTab.tsx         # Cloud execution + admin console
├── worker/
│   ├── marketos_worker.py          # Windows VPS worker service
│   └── setup_worker.ps1            # 1-click worker setup
├── docs/
│   └── cloud_mt5_bridge_guide.md   # Operational runbook
└── replay_archive/                  # Historical simulation batches
```

---

## Execution Architecture

```
Subscriber (any device / browser)
        ↓  HTTPS via Cloudflare Tunnel
Market OS Backend (FastAPI · port 8000)
        ↓
Cloud Execution Router (multi-tenant · in-memory queues)
        ↓
Windows Worker (marketos_worker.py)
        ↓
MT5 Terminal Sessions (isolated per broker account)
        ↓
Individual Broker Accounts
```

**Guardrails applied per position:**
- `-0.35R` MAE early invalidation
- `+0.35R` MFE disarm
- `≤ 2.5 pip` spread check before entry
- Per-account and global killswitch
- AES-256 encrypted broker credentials at rest

---

## Deployment

**Soft launch (current):** Local Windows PC + Cloudflare Tunnel (free, zero infrastructure cost)  
**Scale-up path:** Windows VPS (worker) + named Cloudflare Tunnel (permanent URL)

---

## Access

Authorised subscribers access the platform via the live URL shared by the administrator. No installation required — runs entirely in the browser.

Admin portal: `Execution → Admin Operations Console`
