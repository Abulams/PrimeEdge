# Market OS — Cloud MT5 Execution Bridge Operational Runbook

## Overview
The Cloud MT5 Execution Bridge is a zero-install cloud execution service for subscribers.
Subscribers connect via web without installing EAs or running Python.
One Windows VPS worker manages up to 10 isolated MT5 terminal sessions.

## 1. Cloud-to-Worker Architecture
- **Cloud API (`backend/app`):** Orchestrates multi-tenant order queues, encryption, and solo-founder admin dashboard.
- **Worker (`worker/marketos_worker.py`):** Runs on Windows VPS, manages local MT5 sessions, and runs local sub-second -0.35R MAE early invalidation loops.

## 2. Master Emergency Controls
- **Global Killswitch:** Accessible from Admin Operations Console or `POST /api/v1/execution/admin/killswitch/global`. Instantly pauses order dispatching across all workers.
- **Per-Account Killswitch:** Pauses auto-execution for individual subscriber accounts.

## 3. Worker Setup (1-Click)
Run on Windows VPS:
```powershell
.\worker\setup_worker.ps1
```
