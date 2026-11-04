"""
PrimeEdge Video Service
Wraps Remotion CLI renders. Called by video_render router.
"""

import json
import os
import shutil
import subprocess
import time
from datetime import datetime
from fastapi import HTTPException

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_ENGINE_ROOT = os.environ.get(
    "VIDEO_ENGINE_DIR",
    os.path.join(_REPO_ROOT, "video-engine"),
)
RENDER_SCRIPT = os.environ.get(
    "VIDEO_ENGINE_RENDER_SCRIPT",
    os.path.join(_ENGINE_ROOT, "render.mjs"),
)
_DEFAULT_OUTPUT = (
    os.path.join(_ENGINE_ROOT, "out")
    if os.name == "nt"
    else "/tmp/primeedge_renders"
)
RENDER_OUTPUT_DIR = os.environ.get("VIDEO_RENDER_OUTPUT_DIR", _DEFAULT_OUTPUT)
MAX_RENDER_AGE_SECONDS = 3600  # 1 hour
RENDER_TIMEOUT_SECONDS = 600


def _node_bin() -> str:
    override = os.environ.get("NODE_BIN")
    if override and os.path.isfile(override):
        return override
    which = shutil.which("node")
    if which:
        return which
    for candidate in (
        r"C:\Program Files\nodejs\node.exe",
        r"C:\Program Files (x86)\nodejs\node.exe",
    ):
        if os.path.isfile(candidate):
            return candidate
    raise HTTPException(
        status_code=503,
        detail="Video render engine not available: Node.js is not installed on this server.",
    )


def _cleanup_old_renders() -> None:
    """Remove render files older than 1 hour from the output directory."""
    if not os.path.isdir(RENDER_OUTPUT_DIR):
        return
    now = time.time()
    for fname in os.listdir(RENDER_OUTPUT_DIR):
        fpath = os.path.join(RENDER_OUTPUT_DIR, fname)
        try:
            if os.path.isfile(fpath) and (now - os.path.getmtime(fpath)) > MAX_RENDER_AGE_SECONDS:
                os.remove(fpath)
        except OSError:
            pass


def _run_render(composition: str, props: dict) -> str:
    """
    Shared subprocess runner for all Remotion compositions.

    Args:
        composition: The Remotion composition ID (e.g. 'SignalCard').
        props: Dictionary of props to pass as JSON to the render script.

    Returns:
        Absolute path of the rendered MP4 file.
    """
    os.makedirs(RENDER_OUTPUT_DIR, exist_ok=True)
    _cleanup_old_renders()

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
    output_path = os.path.join(RENDER_OUTPUT_DIR, f"{composition}_{timestamp}.mp4")
    props_json = json.dumps(props)
    node = _node_bin()

    try:
        subprocess.run(
            [node, "--version"],
            check=True,
            capture_output=True,
            timeout=10,
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Video render engine not available: Node.js is not installed on this server.",
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=503,
            detail="Video render engine not available: Node.js health-check timed out.",
        )

    env = os.environ.copy()
    node_dir = os.path.dirname(node)
    env["PATH"] = node_dir + os.pathsep + env.get("PATH", "")

    try:
        subprocess.run(
            [
                node,
                RENDER_SCRIPT,
                "--composition", composition,
                "--props", props_json,
                "--output", output_path,
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=RENDER_TIMEOUT_SECONDS,
            cwd=_ENGINE_ROOT,
            env=env,
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Video render engine not available: render script not found at {RENDER_SCRIPT}. "
                "Ensure the video-engine is deployed."
            ),
        )
    except subprocess.CalledProcessError as exc:
        stderr_snippet = (exc.stderr or exc.stdout or "")[-800:]
        raise HTTPException(
            status_code=500,
            detail=f"Render failed for composition '{composition}': {stderr_snippet}",
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=500,
            detail=f"Render timed out after {RENDER_TIMEOUT_SECONDS} s for composition '{composition}'.",
        )

    if not os.path.isfile(output_path):
        raise HTTPException(
            status_code=500,
            detail=f"Render completed but output file was not found at {output_path}.",
        )

    return output_path


def render_signal_card(data: dict) -> str:
    """Renders the SignalCard Remotion composition."""
    props = {
        "instrument": data.get("instrument", "XAUUSD"),
        "direction": data.get("direction", "LONG"),
        "status_state": data.get("status_state", "WAIT"),
        "mss_score": data.get("mss_score", 0.0),
        "current_regime": data.get("current_regime", ""),
        "continuation_probability": data.get("continuation_probability", 0.0),
        "best_session": data.get("best_session", ""),
        "historical_sample_size": data.get("historical_sample_size", 0),
        "evidence_strength": data.get("evidence_strength", "Moderate"),
        "why_this_now": data.get("why_this_now", ""),
        "acceptable_corridor": data.get("acceptable_corridor"),
        "mae_data": data.get("mae_data"),
        "preferred_zone": data.get("preferred_zone"),
        "trade_thesis": data.get("trade_thesis"),
    }
    props = {k: v for k, v in props.items() if v is not None}
    return _run_render("SignalCard", props)


def render_weekly_wrapped(data: dict) -> str:
    """Renders the WeeklyWrapped Remotion composition."""
    best = data.get("best_trade") or {
        "instrument": "—",
        "pnl_pips": 0,
        "direction": "LONG",
    }
    props = {
        "user_name": data.get("user_name", "Trader"),
        "week_label": data.get("week_label", ""),
        "total_setups": data.get("total_setups", data.get("total_trades", 0)),
        "setups_taken": data.get("setups_taken", data.get("total_trades", 0)),
        "win_rate": data.get("win_rate", 0.0),
        "avg_r_multiple": data.get("avg_r_multiple", data.get("avg_r", 0.0)),
        "total_pnl_pips": data.get("total_pnl_pips", 0.0),
        "best_trade": best,
        "instruments_traded": data.get("instruments_traded", []),
        "mae_discipline": data.get("mae_discipline", 0.0),
    }
    props = {k: v for k, v in props.items() if v is not None}
    return _run_render("WeeklyWrapped", props)


def render_macro_daily(data: dict) -> str:
    """Renders the MacroDaily Remotion composition."""
    date_label = data.get("date_label") or data.get("date") or datetime.utcnow().strftime("%d %b %Y")
    key_instruments = data.get("key_instruments") or data.get("top_instruments") or []
    props = {
        "date_label": date_label,
        "dxy_level": data.get("dxy_level", 104.0),
        "dxy_change_pct": data.get("dxy_change_pct", 0.0),
        "vix_level": data.get("vix_level", 18.0),
        "vix_change_pct": data.get("vix_change_pct", 0.0),
        "risk_sentiment": data.get("risk_sentiment", "NEUTRAL"),
        "macro_headline": data.get("macro_headline") or data.get("macro_summary") or "",
        "key_instruments": key_instruments,
        "session_open": data.get("session_open", "London"),
    }
    props = {k: v for k, v in props.items() if v is not None}
    return _run_render("MacroDaily", props)
