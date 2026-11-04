# Market-OS Migration Guide (Zero-Cost / Free Trial Setup)

This guide walks you through migrating Market-OS to either:
- **Option A: Your Personal Windows Laptop/PC (100% Free Forever)**
- **Option B: A Free Trial Cloud VPS (Google Cloud $300 Credit / Azure $200 Credit)**

---

## What is in Your Backup Bundle
1. `backend/market_os.db` — SQLite database with all accounts, trades, setups, and history.
2. `backend/.env` — Environment configuration, master keys, and broker secrets.
3. `requirements_full.txt` — Exact list of all Python dependencies.
4. `setup_new_machine.ps1` — 1-click automated setup script.

---

## Option A: Run Free on Personal Laptop / PC ($0 Forever)

### Step 1: Install Prerequisites
1. Download and install **Python 3.11** from [python.org](https://www.python.org/downloads/windows/).
   - **IMPORTANT:** Check the box that says `"Add python.exe to PATH"`.
2. Download and install **Git** from [git-scm.com](https://git-scm.com/download/win).
3. Download and install standard **MetaTrader 5** from [metatrader5.com](https://www.metatrader5.com/en/download).

### Step 2: Clone the Repository
Open PowerShell and run:
```powershell
cd C:\
git clone https://github.com/Abulamido/Market-OS.git
```

### Step 3: Copy Your Data Files
Extract your migration bundle into `C:\Market-OS`:
- Place `market_os.db` into `C:\Market-OS\backend\`
- Place `.env` into `C:\Market-OS\backend\`
- Place `requirements_full.txt` into `C:\Market-OS\`

### Step 4: Run the Setup Script
Open PowerShell as Administrator and run:
```powershell
powershell -ExecutionPolicy Bypass -File C:\Market-OS\setup_new_machine.ps1
```

### Step 5: Start Market-OS
Run:
```powershell
python C:\Market-OS\watchdog.py
```

### (Optional) Access from Anywhere (Phone / Outside Home) via Cloudflare Tunnel
1. Download **Cloudflared** (free) from [cloudflare.com](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/).
2. Run: `cloudflared tunnel --url http://localhost:8000`
3. Cloudflare will give you a free, permanent HTTPS URL that you can open from your phone anywhere in the world with zero router port forwarding.

---

## Option B: Free Trial Cloud VPS (GCP $300 or Azure $200)

### 1. Google Cloud Platform ($300 Credit for 90 Days)
1. Go to [cloud.google.com/free](https://cloud.google.com/free) and sign up with any Google account.
2. Navigate to **Compute Engine > VM Instances > Create Instance**.
3. Settings:
   - **Region:** `europe-west2` (London) or `europe-west3` (Frankfurt)
   - **Machine Type:** `e2-standard-2` (2 vCPU, 8 GB RAM)
   - **Boot Disk:** Change to **Windows Server 2022 Datacenter** (Standard persistent disk, 50 GB)
   - **Firewall:** Allow HTTP and HTTPS
4. Click **Create**, then click **RDP** to connect to your new VPS desktop.
5. Inside the VPS, follow Steps 1–5 from Option A above!

---

## Ongoing Backups
Market-OS automatically creates daily timestamped backups of `market_os.db` inside `C:\Market-OS\backups\`. You can sync this folder to Google Drive or OneDrive for continuous off-site safety.
