"""
PrimeEdge VPS Node.js Setup Script
Installs Node.js 20 LTS on the VPS and sets up the Remotion video-engine.
Run this script from your local machine (requires: pip install paramiko scp).

Usage:
    python vps_setup_node.py
"""

import os
import sys
import tarfile
import time

try:
    import paramiko
    from scp import SCPClient
except ImportError:
    print("[ERROR] Missing dependencies. Install them with:")
    print("        pip install paramiko scp")
    sys.exit(1)

# ---------------------------------------------------------------------------
# VPS credentials
# ---------------------------------------------------------------------------
VPS_HOST = "172.237.112.138"
VPS_USER = "root"
VPS_PASS = "AbubakarLamido556@"

VIDEO_ENGINE_REMOTE_DIR = "/opt/market-os/video-engine"
RENDER_TMP_DIR = "/tmp/primeedge_renders"

# Local path to the video-engine folder (relative to this script's location)
LOCAL_VIDEO_ENGINE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "video-engine")


# ---------------------------------------------------------------------------
# SSH helpers
# ---------------------------------------------------------------------------

def _connect() -> paramiko.SSHClient:
    """Create and return an authenticated SSH client."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    print(f"[SSH] Connecting to {VPS_HOST} as {VPS_USER} …")
    client.connect(VPS_HOST, username=VPS_USER, password=VPS_PASS, timeout=30)
    print("[SSH] Connected.")
    return client


def _run(client: paramiko.SSHClient, cmd: str, description: str = "", raise_on_error: bool = True) -> str:
    """Execute a shell command over SSH, print output, and return stdout."""
    label = description or cmd[:80]
    print(f"\n[CMD] {label}")
    print(f"      $ {cmd}")

    stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
    out = ""
    for line in iter(stdout.readline, ""):
        print(f"      {line}", end="")
        out += line

    exit_code = stdout.channel.recv_exit_status()
    if raise_on_error and exit_code != 0:
        err = stderr.read().decode(errors="replace")
        raise RuntimeError(
            f"Command failed (exit {exit_code}): {cmd}\nSTDERR: {err}"
        )
    return out


# ---------------------------------------------------------------------------
# Step implementations
# ---------------------------------------------------------------------------

def step_install_nodejs(client: paramiko.SSHClient) -> None:
    """Step 1: Install Node.js 20 LTS via NodeSource."""
    print("\n" + "=" * 60)
    print("STEP 1: Installing Node.js 20 LTS")
    print("=" * 60)
    _run(client, "curl -fsSL https://deb.nodesource.com/setup_20.x | bash -",
         "Add NodeSource repo")
    _run(client, "apt-get install -y nodejs",
         "Install nodejs package")
    _run(client, "node --version && npm --version",
         "Verify Node.js and npm versions")


def step_create_directories(client: paramiko.SSHClient) -> None:
    """Step 2 & 3: Create required directories on the VPS."""
    print("\n" + "=" * 60)
    print("STEP 2–3: Creating directories")
    print("=" * 60)
    _run(client, f"mkdir -p {VIDEO_ENGINE_REMOTE_DIR}",
         f"Create video-engine dir: {VIDEO_ENGINE_REMOTE_DIR}")
    _run(client, f"mkdir -p {RENDER_TMP_DIR} && chmod 777 {RENDER_TMP_DIR}",
         f"Create renders tmp dir: {RENDER_TMP_DIR}")


def step_upload_video_engine(client: paramiko.SSHClient) -> None:
    """Step 4: Upload local video-engine/ folder to VPS via SCP."""
    print("\n" + "=" * 60)
    print("STEP 4: Uploading video-engine to VPS")
    print("=" * 60)

    if not os.path.isdir(LOCAL_VIDEO_ENGINE_DIR):
        print(f"[WARN] Local video-engine directory not found at: {LOCAL_VIDEO_ENGINE_DIR}")
        print("       Skipping upload. Deploy manually if needed.")
        return

    # Collect all files in the video-engine directory recursively
    files_to_upload: list[tuple[str, str]] = []
    for root, dirs, files in os.walk(LOCAL_VIDEO_ENGINE_DIR):
        # Skip node_modules — will be installed fresh on the VPS
        dirs[:] = [d for d in dirs if d != "node_modules"]
        for fname in files:
            local_path = os.path.join(root, fname)
            # Compute path relative to LOCAL_VIDEO_ENGINE_DIR
            rel_path = os.path.relpath(local_path, LOCAL_VIDEO_ENGINE_DIR)
            remote_path = f"{VIDEO_ENGINE_REMOTE_DIR}/{rel_path.replace(os.sep, '/')}"
            files_to_upload.append((local_path, remote_path))

    print(f"[SCP] Uploading {len(files_to_upload)} file(s) …")
    with SCPClient(client.get_transport()) as scp:
        for local_path, remote_path in files_to_upload:
            # Ensure parent directory exists on remote
            remote_dir = remote_path.rsplit("/", 1)[0]
            client.exec_command(f"mkdir -p {remote_dir}")
            time.sleep(0.05)  # give the mkdir a moment
            scp.put(local_path, remote_path)
            print(f"      ✓ {local_path}  →  {remote_path}")

    print("[SCP] Upload complete.")


def step_npm_install(client: paramiko.SSHClient) -> None:
    """Step 5: Run npm install in the video-engine directory on VPS."""
    print("\n" + "=" * 60)
    print("STEP 5: Running npm install on VPS")
    print("=" * 60)
    _run(client, f"cd {VIDEO_ENGINE_REMOTE_DIR} && npm install",
         "npm install (this may take a minute …)")


def step_test_render(client: paramiko.SSHClient) -> None:
    """Step 6: Run a test render on the VPS to validate the engine."""
    print("\n" + "=" * 60)
    print("STEP 6: Running test render")
    print("=" * 60)

    test_props = (
        '{"instrument":"XAUUSD","direction":"LONG","status_state":"READY",'
        '"mss_score":0.82,"current_regime":"RISK_ON | DXY_WEAK",'
        '"continuation_probability":0.74,"best_session":"London",'
        '"historical_sample_size":147,"evidence_strength":"Strong",'
        '"why_this_now":"MSS confirmed above 1-hour structure with DXY weakness aligning",'
        '"acceptable_corridor":{"p25_price":2318.50,"p75_price":2321.00,"p90_invalidation":2315.00},'
        '"mae_data":{"p25_pips":8,"p50_pips":14,"p75_pips":22,"p90_pips":31}}'
    )

    test_output = f"{RENDER_TMP_DIR}/test_signal_card.mp4"
    render_cmd = (
        f"node {VIDEO_ENGINE_REMOTE_DIR}/render.mjs "
        f"--composition SignalCard "
        f"--props '{test_props}' "
        f"--output {test_output}"
    )
    _run(client, render_cmd, "Test SignalCard render")


def step_verify_output(client: paramiko.SSHClient) -> None:
    """Step 7: Verify the test render output file exists."""
    print("\n" + "=" * 60)
    print("STEP 7: Verifying output file")
    print("=" * 60)
    test_output = f"{RENDER_TMP_DIR}/test_signal_card.mp4"
    out = _run(client, f"ls -lh {test_output}", "Check test render output")
    if test_output in out or ".mp4" in out:
        print("\n[✓] Test render SUCCESSFUL — output file confirmed on VPS.")
    else:
        print("\n[✗] Output file NOT found. Check render logs above.")


def step_print_router_instructions() -> None:
    """Step 8: Print instructions for registering the video router in main.py."""
    print("\n" + "=" * 60)
    print("STEP 8: Register video router in FastAPI main.py")
    print("=" * 60)
    print(
        """
Add the following lines to:
  Market-OS/backend/app/main.py

  ── After the existing router imports (around line 180) ──

    from .routers.video_render import router as video_render_router

  ── After the existing app.include_router() calls ──

    app.include_router(video_render_router)

The router exposes:
  POST  /api/v1/video/signal-card      — renders SignalCard MP4 for an instrument
  POST  /api/v1/video/weekly-wrapped   — renders WeeklyWrapped MP4 for a user/week
  GET   /api/v1/video/macro-daily      — renders MacroDaily MP4 from current regime
"""
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    client = None
    try:
        client = _connect()

        step_install_nodejs(client)
        step_create_directories(client)
        step_upload_video_engine(client)
        step_npm_install(client)
        step_test_render(client)
        step_verify_output(client)

        print("\n" + "=" * 60)
        print("[✓] VPS Node.js setup complete!")
        print("=" * 60)

    except Exception as exc:
        print(f"\n[ERROR] Setup failed: {exc}")
        sys.exit(1)
    finally:
        if client:
            client.close()
            print("\n[SSH] Connection closed.")

    # Always print registration instructions (no SSH required)
    step_print_router_instructions()


if __name__ == "__main__":
    main()
